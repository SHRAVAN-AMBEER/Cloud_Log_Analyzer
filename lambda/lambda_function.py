import json
import boto3
from datetime import datetime, timedelta
from collections import defaultdict
from botocore.exceptions import ClientError

# AWS Clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# DynamoDB Tables (Week 4-5)
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')

# Configuration
BATCH_SIZE = 25  # DynamoDB batch write limit
FAILED_LOGIN_THRESHOLD = 3
PASSWORD_SPRAY_THRESHOLD = 5
TIME_WINDOW_MINUTES = 15
MAX_LOGINS_PER_MINUTE = 10


def batch_write_to_dynamodb(table, items):
    """
    Batch write items to DynamoDB (optimized performance)
    Handles batch size limit (25 items per request)
    """
    if not items:
        return 0
    
    written = 0
    try:
        with table.batch_writer(
            batch_size=BATCH_SIZE,
            overwrite_by_pkey=False
        ) as batch:
            for item in items:
                try:
                    batch.put_item(Item=item)
                    written += 1
                except Exception as e:
                    print(f"⚠️ Batch write item failed: {e}")
                    continue
    except ClientError as e:
        print(f"❌ DynamoDB batch write error: {e}")
    
    return written


def validate_log_entry(log):
    """Validate log entry has required fields"""
    required_fields = ['username', 'timestamp', 'ip', 'status']
    return all(log.get(field) for field in required_fields)


def calculate_severity(threat_type, count):
    """Calculate severity score based on threat type and count"""
    severity_map = {
        'MULTIPLE_FAILED_LOGINS': {3: 'MEDIUM', 5: 'HIGH', 10: 'CRITICAL'},
        'PASSWORD_SPRAY': {5: 'HIGH', 10: 'CRITICAL'},
        'VELOCITY_ABUSE': {10: 'HIGH', 20: 'CRITICAL'},
        'IMPOSSIBLE_TRAVEL': {1: 'CRITICAL'},
        'UNUSUAL_TIME_LOGIN': {1: 'LOW', 3: 'MEDIUM'},
        'NEW_LOCATION': {1: 'LOW'},
        'REPEATED_FAILED_ATTEMPTS': {5: 'HIGH', 10: 'CRITICAL'}
    }
    
    thresholds = severity_map.get(threat_type, {})
    severity = 'LOW'
    for threshold, level in sorted(thresholds.items()):
        if count >= threshold:
            severity = level
    
    return severity


def create_alert_item(username, ip, threat_type, severity, count, additional_data=None):
    """Create a standardized alert item"""
    alert = {
        'user_id': username,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'ip': ip,
        'threat_flag': True,
        'alert_type': threat_type,
        'severity': severity,
        'status': 'ACTIVE',
        'count': count
    }
    
    if additional_data:
        alert.update(additional_data)
    
    return alert


# WEEK 5: Advanced Anomaly Detection Rules

def detect_multiple_failed_logins(logs):
    """Rule 1: Detect multiple failed login attempts (3+)"""
    alerts = []
    failed_count = defaultdict(int)
    
    for log in logs:
        if log.get('status') == 'failure':
            user_key = (log.get('username'), log.get('ip'))
            failed_count[user_key] += 1
    
    for (username, ip), count in failed_count.items():
        if count >= FAILED_LOGIN_THRESHOLD:
            severity = calculate_severity('MULTIPLE_FAILED_LOGINS', count)
            alert = create_alert_item(username, ip, 'MULTIPLE_FAILED_LOGINS', severity, count)
            alerts.append(alert)
            print(f"🚨 RULE 1: Multiple failed logins - {username} from {ip}: {count} attempts")
    
    return alerts


def detect_password_spray(logs):
    """Rule 2: Detect password spray attacks (many users from same IP)"""
    alerts = []
    ip_user_map = defaultdict(set)
    
    for log in logs:
        if log.get('status') == 'failure':
            ip = log.get('ip')
            username = log.get('username')
            ip_user_map[ip].add(username)
    
    for ip, users in ip_user_map.items():
        if len(users) >= PASSWORD_SPRAY_THRESHOLD:
            severity = calculate_severity('PASSWORD_SPRAY', len(users))
            alert = create_alert_item('SYSTEM', ip, 'PASSWORD_SPRAY', severity, len(users),
                                     {'affected_users': len(users)})
            alerts.append(alert)
            print(f"🚨 RULE 2: Password spray attack - {ip} targeting {len(users)} users")
    
    return alerts


def detect_velocity_abuse(logs):
    """Rule 3: Detect velocity abuse (too many logins in short time period)"""
    alerts = []
    user_logins = defaultdict(list)
    
    for log in logs:
        username = log.get('username')
        try:
            timestamp = datetime.fromisoformat(log.get('timestamp').replace('Z', '+00:00'))
            user_logins[username].append(timestamp)
        except (ValueError, AttributeError):
            continue
    
    for username, timestamps in user_logins.items():
        timestamps.sort()
        for i in range(len(timestamps) - MAX_LOGINS_PER_MINUTE + 1):
            window_start = timestamps[i]
            window_end = window_start + timedelta(minutes=1)
            logins_in_window = sum(1 for ts in timestamps if window_start <= ts <= window_end)
            
            if logins_in_window > MAX_LOGINS_PER_MINUTE:
                severity = calculate_severity('VELOCITY_ABUSE', logins_in_window)
                alert = create_alert_item(username, 'UNKNOWN', 'VELOCITY_ABUSE', severity, logins_in_window)
                alerts.append(alert)
                print(f"🚨 RULE 3: Velocity abuse - {username}: {logins_in_window} logins in 1 minute")
                break
    
    return alerts


def detect_unusual_time_login(logs):
    """Rule 4: Detect logins at unusual times (off-hours: 10 PM - 6 AM)"""
    alerts = []
    unusual_logins = defaultdict(list)
    
    for log in logs:
        if log.get('status') == 'success':
            try:
                timestamp = datetime.fromisoformat(log.get('timestamp').replace('Z', '+00:00'))
                hour = timestamp.hour
                
                # Off-hours: 22:00 - 06:00
                if hour >= 22 or hour < 6:
                    username = log.get('username')
                    ip = log.get('ip')
                    unusual_logins[(username, ip)].append(timestamp)
            except (ValueError, AttributeError):
                continue
    
    for (username, ip), timestamps in unusual_logins.items():
        if len(timestamps) >= 2:
            severity = calculate_severity('UNUSUAL_TIME_LOGIN', len(timestamps))
            alert = create_alert_item(username, ip, 'UNUSUAL_TIME_LOGIN', severity, len(timestamps))
            alerts.append(alert)
            print(f"🚨 RULE 4: Unusual time logins - {username} from {ip}: {len(timestamps)} off-hours attempts")
    
    return alerts


def detect_repeated_failed_attempts(logs):
    """Rule 5: Detect repeated failed attempts with time-based analysis"""
    alerts = []
    failed_attempts = defaultdict(list)
    
    for log in logs:
        if log.get('status') == 'failure':
            try:
                timestamp = datetime.fromisoformat(log.get('timestamp').replace('Z', '+00:00'))
                user_key = (log.get('username'), log.get('ip'))
                failed_attempts[user_key].append(timestamp)
            except (ValueError, AttributeError):
                continue
    
    for (username, ip), timestamps in failed_attempts.items():
        if len(timestamps) >= 5:
            # Check if attempts are within time window
            timestamps.sort()
            if timestamps[-1] - timestamps[0] <= timedelta(minutes=TIME_WINDOW_MINUTES):
                severity = calculate_severity('REPEATED_FAILED_ATTEMPTS', len(timestamps))
                alert = create_alert_item(username, ip, 'REPEATED_FAILED_ATTEMPTS', severity, len(timestamps),
                                        {'time_window_minutes': TIME_WINDOW_MINUTES})
                alerts.append(alert)
                print(f"🚨 RULE 5: Repeated failed attempts - {username} from {ip}: {len(timestamps)} in {TIME_WINDOW_MINUTES} min")
    
    return alerts


def detect_new_location_login(logs, historical_ips=None):
    """Rule 6: Detect login from new/unusual location (new IP for user)"""
    alerts = []
    user_ips = defaultdict(set)
    
    # In production, historical_ips would come from DynamoDB
    if historical_ips is None:
        historical_ips = {}
    
    for log in logs:
        if log.get('status') == 'success':
            username = log.get('username')
            ip = log.get('ip')
            user_ips[username].add(ip)
    
    for username, ips in user_ips.items():
        known_ips = historical_ips.get(username, set())
        new_ips = ips - known_ips
        
        if new_ips and len(known_ips) > 0:  # Only alert if user has history
            for new_ip in new_ips:
                severity = calculate_severity('NEW_LOCATION', 1)
                alert = create_alert_item(username, new_ip, 'NEW_LOCATION', severity, 1,
                                        {'is_new_ip': True})
                alerts.append(alert)
                print(f"🚨 RULE 6: New location login - {username} from new IP {new_ip}")
    
    return alerts


def detect_account_lockout_patterns(logs):
    """Rule 7: Detect potential account lockout attacks"""
    alerts = []
    failed_by_user = defaultdict(int)
    
    for log in logs:
        if log.get('status') == 'failure':
            username = log.get('username')
            failed_by_user[username] += 1
    
    for username, count in failed_by_user.items():
        if count >= 10:  # Potential lockout attack
            severity = calculate_severity('REPEATED_FAILED_ATTEMPTS', count)
            alert = create_alert_item(username, 'UNKNOWN', 'ACCOUNT_LOCKOUT_ATTEMPT', severity, count,
                                    {'attack_type': 'brute_force_lockout'})
            alerts.append(alert)
            print(f"🚨 RULE 7: Account lockout attempt - {username}: {count} failed attempts")
    
    return alerts


def lambda_handler(event, context):
    """
    WEEK 5: Enhanced Lambda with advanced anomaly detection
    - 7 detection rules
    - Batch DynamoDB writes (performance optimized)
    - Comprehensive error handling
    - Edge case validation
    """
    print("🚀 Lambda started - WEEK 5 Advanced Anomaly Detection")
    
    try:
        # Validate event structure
        if 'Records' not in event or not event['Records']:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No S3 records in event"})
            }
        
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        print(f"📦 Processing: s3://{bucket}/{key}")
        
        # Fetch and parse logs
        try:
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
        except Exception as e:
            print(f"❌ S3 read error: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"S3 read failed: {str(e)}"})
            }
        
        # Parse logs with validation
        logs = []
        invalid_count = 0
        
        for line_num, line in enumerate(content.splitlines(), 1):
            if not line.strip():
                continue
            
            try:
                log_entry = json.loads(line)
                if validate_log_entry(log_entry):
                    logs.append(log_entry)
                else:
                    print(f"⚠️ Line {line_num}: Missing required fields")
                    invalid_count += 1
            except json.JSONDecodeError:
                print(f"⚠️ Line {line_num}: Invalid JSON")
                invalid_count += 1
        
        print(f"✅ Parsed {len(logs)} valid logs ({invalid_count} invalid)")
        
        if not logs:
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "total_logs": 0,
                    "alerts_detected": 0,
                    "message": "No valid logs to process"
                })
            }
        
        # Prepare batch write items
        processed_items = []
        for log in logs:
            processed_items.append({
                'user_id': log.get('username', 'UNKNOWN'),
                'timestamp': log.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                'ip': log.get('ip', 'UNKNOWN'),
                'threat_flag': False,
                'user_agent': log.get('user_agent', 'UNKNOWN'),
                'login_status': log.get('status', 'unknown'),
                'processed_at': datetime.utcnow().isoformat() + 'Z'
            })
        
        # Batch write processed logs (optimized)
        logs_written = batch_write_to_dynamodb(PROCESSED_LOGS_TABLE, processed_items)
        print(f"✅ Stored {logs_written}/{len(logs)} logs in ProcessedLogs table")
        
        # Run all 7 anomaly detection rules
        all_alerts = []
        
        all_alerts.extend(detect_multiple_failed_logins(logs))
        all_alerts.extend(detect_password_spray(logs))
        all_alerts.extend(detect_velocity_abuse(logs))
        all_alerts.extend(detect_unusual_time_login(logs))
        all_alerts.extend(detect_repeated_failed_attempts(logs))
        all_alerts.extend(detect_new_location_login(logs))
        all_alerts.extend(detect_account_lockout_patterns(logs))
        
        # Remove duplicate alerts (same user_id, timestamp, alert_type)
        seen = set()
        unique_alerts = []
        for alert in all_alerts:
            key = (alert['user_id'], alert['timestamp'], alert['alert_type'])
            if key not in seen:
                seen.add(key)
                unique_alerts.append(alert)
        
        print(f"🔍 Detection complete: {len(unique_alerts)} unique alerts")
        
        # Batch write alerts (optimized)
        alerts_written = batch_write_to_dynamodb(ALERTS_TABLE, unique_alerts)
        print(f"✅ Stored {alerts_written}/{len(unique_alerts)} alerts in SecurityAlerts table")
        
        # Success response
        return {
            "statusCode": 200,
            "body": json.dumps({
                "total_logs": len(logs),
                "logs_stored": logs_written,
                "alerts_detected": alerts_written,
                "invalid_logs": invalid_count,
                "message": "WEEK 5: Advanced anomaly detection complete",
                "rules_executed": 7
            })
        }
    
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }