# SQS TRIGGER SETTINGS (set in AWS Console):
# Batch size: 10-100 messages per invocation
# Batch window: 5 seconds
# This ensures ML model receives enough logs to detect behavioral patterns
import os
import json
import boto3
from datetime import datetime
from collections import defaultdict
from botocore.exceptions import ClientError
from decimal import Decimal
import uuid
import urllib.request
import urllib.error
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# AWS Clients
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Cross-account role ARN
CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::502881461360:role/DynamoDBCrossAccountRole"

def get_dynamodb():
    try:
        sts_client = boto3.client('sts')
        cross_account_arn = os.getenv("CROSS_ACCOUNT_ROLE_ARN", CROSS_ACCOUNT_ROLE_ARN)
        
        assumed_role = sts_client.assume_role(
            RoleArn=cross_account_arn,
            RoleSessionName="LambdaSession"
        )

        credentials = assumed_role['Credentials']

        return boto3.resource(
            'dynamodb',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
    except Exception as e:
        print(f"⚠️ Cross-account assumption failed. Falling back to Lambda execution role. Error: {e}")
        return boto3.resource('dynamodb')

# =========================
# CONFIG & ENV VARS
# =========================
# Get Email Config from environment variables
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")  # Your Gmail
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "") # Your App Password
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", SMTP_EMAIL)
DEFAULT_COMPANY_ID = "TECH_007"
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5173")

FAILED_LOGIN_THRESHOLD = 3
PASSWORD_SPRAY_THRESHOLD = 5
MAX_LOGINS_PER_MINUTE = 10
# =========================
# UTILS
# =========================
GEO_CACHE = {}
COMPANY_CACHE = {} # Cache for company contact details

def get_company_contact(dynamodb, company_id):
    """Fetch registered email for a specific company with caching"""
    if not company_id or company_id == 'UNKNOWN':
        return None
        
    if company_id in COMPANY_CACHE:
        return COMPANY_CACHE[company_id]
        
    try:
        table = dynamodb.Table('Companies')
        response = table.get_item(Key={'company_id': company_id})
        item = response.get('Item')
        if item and item.get('email'):
            contact = {'email': item.get('email')}
            COMPANY_CACHE[company_id] = contact
            return contact
    except Exception as e:
        print(f"⚠️ Error fetching contact for {company_id}: {e}")
        
    return None

def get_real_geo(ip):
    """Real-time Geo-IP lookup with in-memory caching and CIDR cleaning"""
    if not ip or ip == "UNKNOWN" or "->" in ip:
        if "->" in ip:
            return get_real_geo(ip.split("->")[-1].strip())
        return 0.0, 0.0, "Unknown"

    # Clean IP: Strip CIDR notation (e.g., "104.0.0.0/8" -> "104.0.0.0")
    clean_ip = ip.split('/')[0].strip()

    if clean_ip in GEO_CACHE:
        return GEO_CACHE[clean_ip]

    try:
        # Using ip-api.com (Free for non-commercial use)
        url = f"http://ip-api.com/json/{clean_ip}?fields=status,message,country,lat,lon"
        with urllib.request.urlopen(url, timeout=3) as response:
            data = json.loads(response.read().decode())
            if data.get('status') == 'success':
                res = (float(data['lat']), float(data['lon']), data['country'])
                GEO_CACHE[clean_ip] = res
                return res
    except Exception as e:
        print(f"⚠️ Geo-IP lookup failed for {clean_ip}: {e}")
    
    return 0.0, 0.0, "Lookup Failed"

def batch_write_to_dynamodb(table, items):
    if not items:
        return 0

    written = 0
    try:
        with table.batch_writer() as batch:
            for item in items:
                try:
                    batch.put_item(Item=item)
                    written += 1
                except Exception as e:
                    print(f"⚠️ Batch write item failed: {e}")
    except ClientError as e:
        print(f"❌ DynamoDB batch write error: {e}")

    return written

class UniversalLogParser:
    @staticmethod
    def _parse_raw(line):
        if not line or not line.strip(): return None
        try:
            log_dict = json.loads(line)
            # Normalize fields
            username = log_dict.get('username') or log_dict.get('user_id')
            ip = log_dict.get('ip') or log_dict.get('source_ip')
            status = log_dict.get('status') or log_dict.get('login_status')

            if username and ip and status:
                return {
                    'user_id': username,
                    'ip': ip,
                    'status': status,
                    'log_source': log_dict.get('log_source', 'Custom_Auth_API'),
                    'company_id': log_dict.get('company_id'),
                    'timestamp': log_dict.get('timestamp')
                }
            if 'userIdentity' in log_dict and 'eventName' in log_dict:
                return {
                    'user_id': log_dict['userIdentity'].get('userName', 'UNKNOWN'), 'ip': log_dict.get('sourceIPAddress', 'UNKNOWN'),
                    'status': 'success' if log_dict.get('responseElements', {}).get('ConsoleLogin') == 'Success' else 'failure',
                    'timestamp': log_dict.get('eventTime', datetime.utcnow().isoformat() + 'Z'), 'log_source': 'AWS_CloudTrail',
                    'company_id': log_dict.get('company_id')
                }
        except Exception:
            pass
        apache_match = re.match(r'^(?P<ip>\S+) \S+ (?P<user>\S+) \[(?P<time>.*?)\] ".*?" (?P<status>\d+)', line)
        if apache_match:
            d = apache_match.groupdict()
            return {
                'user_id': d['user'] if d['user'] != '-' else 'UNKNOWN', 'ip': d['ip'],
                'status': 'success' if d['status'].startswith('2') or d['status'].startswith('3') else 'failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z', 'log_source': 'Apache_WebServer',
                'company_id': 'UNKNOWN'
            }
        syslog_match = re.search(r'SRC=(?P<ip>\S+).*?USER=(?P<user>\S+).*?STATUS=(?P<status>success|failure|failed|accepted)', line, re.IGNORECASE)
        if syslog_match:
            d = syslog_match.groupdict()
            return {
                'user_id': d['user'], 'ip': d['ip'],
                'status': 'success' if 'accept' in d['status'].lower() or 'success' in d['status'].lower() else 'failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z', 'log_source': 'Cisco_Firewall',
                'company_id': 'UNKNOWN'
            }
        return None

    @staticmethod
    def parse(line):
        parsed = UniversalLogParser._parse_raw(line)
        if not parsed:
            return None
            
        company_id = parsed.get('company_id')
        if not company_id or company_id == 'UNKNOWN':
            # Try to grab it from original raw json again if missing
            try:
                log_dict = json.loads(line)
                company_id = log_dict.get('company_id', 'UNKNOWN')
            except Exception:
                company_id = 'UNKNOWN'
                
        if company_id == 'UNKNOWN' and parsed.get('log_source') == 'AWS_CloudTrail':
            company_id = DEFAULT_COMPANY_ID
            
        parsed['company_id'] = company_id
        # Ensure unique timestamp exists for rule-based detection
        if not parsed.get('timestamp'):
            # Add a tiny random jitter to ensure unique timestamps in sorting
            import time, random
            jitter = random.random() / 1000.0
            parsed['timestamp'] = datetime.fromtimestamp(time.time() + jitter).isoformat() + 'Z'
            
        return parsed

def send_email_alert(alert, recipient_email):
    """Send a professional security alert via free SMTP (e.g. Gmail)"""
    if not SMTP_EMAIL or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials not configured in Lambda env vars. Skipping email.")
        return
        
    if not recipient_email:
        print("⚠️ No recipient email found. Skipping alert.")
        return

    subject = f"🚨 SECURITY ALERT: {alert.get('alert_type')} Detected for {alert.get('company_id')}"
    
    body_text = (
        f"Critical Security Alert\n"
        f"======================\n"
        f"Alert Type: {alert.get('alert_type')}\n"
        f"Company ID: {alert.get('company_id')}\n"
        f"Risk Level: {alert.get('risk_level')}\n"
        f"Risk Score: {alert.get('risk_score')}\n"
        f"User: {alert.get('user_id')}\n"
        f"IP Source: {alert.get('ip')}\n"
        f"Reasons: {', '.join(alert.get('reasons', []))}\n\n"
        f"Please login to your dashboard to investigate: {DASHBOARD_URL}\n"
    )

    msg = MIMEMultipart()
    msg['From'] = SMTP_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ SMTP Security Email sent to {recipient_email}")
    except Exception as e:
        print(f"❌ SMTP Email error for {recipient_email}: {e}")

def send_company_email_alert(dynamodb, company_id, alert_count):
    print(f"Lean: Skipping SES Email for now. Would send {alert_count} alerts for company {company_id}.")


# =========================
# RULE DETECTION
# =========================
def detect_multiple_failed_logins(logs):
    alerts = []
    failed_count = defaultdict(int)
    ip_company = {}  # track company per (user, ip) key

    for log in logs:
        if log.get('status') == 'failure':
            user = log.get('user_id', 'UNKNOWN')
            ip = log.get('ip', 'UNKNOWN')
            key = (user, ip)
            failed_count[key] += 1
            ip_company[key] = log.get('company_id', 'UNKNOWN')

    for (user, ip), count in failed_count.items():
        if count >= FAILED_LOGIN_THRESHOLD:
            lat, lon, country = get_real_geo(ip)
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
                'company_id': ip_company.get((user, ip), 'UNKNOWN'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': ip,
                'latitude': Decimal(str(lat)),
                'longitude': Decimal(str(lon)),
                'country': country,
                'alert_type': 'MULTIPLE_FAILED_LOGINS',
                'count': Decimal(str(count)),
                'risk_score': Decimal('60'),
                'risk_level': 'MEDIUM',
                'reasons': ['rule_based_multiple_failed']
            })

    return alerts

def detect_password_spray(logs):
    alerts = []
    ip_users = defaultdict(set)
    ip_company = {}

    for log in logs:
        if log.get('status') == 'failure':
            ip = log.get('ip', 'UNKNOWN')
            user = log.get('user_id', 'UNKNOWN')
            ip_users[ip].add(user)
            ip_company[ip] = log.get('company_id', 'UNKNOWN')

    for ip, users in ip_users.items():
        if len(users) >= PASSWORD_SPRAY_THRESHOLD:
            lat, lon, country = get_real_geo(ip)
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': 'SYSTEM',
                'company_id': ip_company.get(ip, 'UNKNOWN'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': ip,
                'latitude': Decimal(str(lat)),
                'longitude': Decimal(str(lon)),
                'country': country,
                'alert_type': 'PASSWORD_SPRAY',
                'count': Decimal(str(len(users))),
                'risk_score': Decimal('90'),
                'risk_level': 'CRITICAL',
                'reasons': ['rule_based_password_spray']
            })

    return alerts

def detect_velocity_abuse(logs):
    alerts = []
    user_times = defaultdict(list)
    user_company = {}

    for log in logs:
        try:
            ts_str = log.get('timestamp', '')
            if 'Z' in ts_str:
                ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            else:
                ts = datetime.now(timezone.utc)
            user = log.get('user_id', 'UNKNOWN')
            user_times[user].append(ts)
            user_company[user] = log.get('company_id', 'UNKNOWN')
        except Exception:
            continue

    # Lower threshold for demo if needed
    THRESHOLD = MAX_LOGINS_PER_MINUTE if len(logs) > 5 else 3
    for user, times in user_times.items():
        if len(times) >= THRESHOLD:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
                'company_id': user_company.get(user, 'UNKNOWN'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': 'UNKNOWN',
                'alert_type': 'VELOCITY_ABUSE',
                'count': Decimal(str(len(times))),
                'risk_score': Decimal('85'),
                'risk_level': 'HIGH',
                'reasons': ['rule_based_velocity_abuse']
            })

    return alerts

def detect_impossible_travel(logs):
    alerts = []
    user_ip_times = defaultdict(list)
    user_company = {}

    for log in logs:
        try:
            ts = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
            user = log.get('user_id', 'UNKNOWN')
            ip = log.get('ip', 'UNKNOWN')
            if user != 'UNKNOWN':
                user_ip_times[user].append((ts, ip))
                user_company[user] = log.get('company_id', 'UNKNOWN')
        except Exception as e:
            print(f"Error parsing log for travel detection: {e}")
            continue

    for user, events in user_ip_times.items():
        if len(events) < 2: continue
        
        # Sort by timestamp
        events.sort()
        for i in range(len(events) - 1):
            t1, ip1 = events[i]
            t2, ip2 = events[i+1]
            
            # If same user, different IP, within 15 minutes = Impossible Travel
            # For testing: if timestamps are identical (time_diff == 0), it still counts!
            time_diff = abs((t2 - t1).total_seconds())
            if ip1 != ip2 and time_diff < 900: # 15 minutes
                lat, lon, country = get_real_geo(ip2)
                alerts.append({
                    'id': str(uuid.uuid4()),
                    'user_id': user,
                    'company_id': user_company.get(user, 'UNKNOWN'),
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'ip': f"{ip1} -> {ip2}",
                    'latitude': Decimal(str(lat)),
                    'longitude': Decimal(str(lon)),
                    'country': country,
                    'alert_type': 'IMPOSSIBLE_TRAVEL',
                    'count': Decimal('1'),
                    'risk_score': Decimal('95'),
                    'risk_level': 'CRITICAL',
                    'reasons': [f"User accessed from {ip1} and {ip2} within {int(time_diff/60)} minutes"]
                })
                break # Only one alert per batch per user

    return alerts


# =========================
# FEATURE EXTRACTION
# =========================
def extract_features(logs):
    # Key = (username, company_id) to keep tenants separate
    user_data = defaultdict(list)
    user_last_ip = {}  # NEW: track last IP per (user, company_id)

    for log in logs:
        key = (log.get('username', 'UNKNOWN'), log.get('company_id', 'UNKNOWN'))
        user_data[key].append(log)
        user_last_ip[key] = log.get('ip', 'UNKNOWN')  # keep overwriting = last IP

    features, usernames, company_ids, ips = [], [], [], []

    for (user, company_id), entries in user_data.items():
        total = len(entries)
        failed = sum(1 for e in entries if e.get('status') == 'failure')
        ip_set = set(e.get('ip', 'UNKNOWN') for e in entries)

        latest = max(entries, key=lambda x: x.get('timestamp', ''))
        try:
            hour = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00')).hour
        except Exception:
            hour = 12  # safe default

        features.append([hour, failed, len(ip_set), failed / total if total else 0])
        usernames.append(user)
        company_ids.append(company_id)
        ips.append(user_last_ip.get((user, company_id), 'UNKNOWN'))

    return features, usernames, company_ids, ips


# =========================
# HYBRID SCORING
# =========================
def compute_risk(feature, ml_prediction):
    login_hour, failed_attempts, ip_count, failure_ratio = feature
    risk_score = 0
    reasons = []

    if ml_prediction == -1:
        risk_score += 50
        reasons.append("ml_anomaly_detected")

    if failure_ratio > 0.5:
        risk_score += 20
        reasons.append("high_failure_rate")

    if ip_count > 3:
        risk_score += 20
        reasons.append("multiple_ips")

    if risk_score > 70:
        level = "CRITICAL"
    elif risk_score > 40:
        level = "HIGH"
    else:
        level = "MEDIUM"

    return risk_score, level, reasons


# =========================
# MAIN LAMBDA
# =========================
def lambda_handler(event, context):
    print("🚀 Lambda started")

    try:
        dynamodb = get_dynamodb()
        logs_table = dynamodb.Table('ProcessedLogs')
        alerts_table = dynamodb.Table('SecurityAlerts')


        if 'Records' not in event or not event['Records']:
            return {"statusCode": 400, "body": json.dumps({"error": "No records in event"})}

        logs = []
        user_sources = defaultdict(set)
        
        is_sqs = 'eventSource' in event['Records'][0] and event['Records'][0]['eventSource'] == 'aws:sqs'
        
        if is_sqs:
            for record in event['Records']:
                body = record.get('body', '')
                parsed = UniversalLogParser.parse(body)
                if parsed:
                    logs.append(parsed)
                    user_sources[parsed.get('username')].add(parsed.get('log_source', 'Unknown'))
        else:
            # S3 Fallback (Original Behavior)
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            for line in content.splitlines():
                parsed = UniversalLogParser.parse(line)
                if parsed:
                    logs.append(parsed)
                    user_sources[parsed.get('username')].add(parsed.get('log_source', 'Unknown'))

        print(f"✅ Parsed {len(logs)} logs")

        # ================= ARCHIVE TO S3 =================
        if logs:
            try:
                timestamp_str = datetime.utcnow().strftime('%Y%m%d%H%M%S')
                s3_key = f"raw-logs/auth/logs_{timestamp_str}_{str(uuid.uuid4())[:8]}.json"
                s3_bucket = "mini-siem-raw-logs-lakshman"
                
                s3.put_object(
                    Bucket=s3_bucket,
                    Key=s3_key,
                    Body=json.dumps(logs, default=str),
                    ContentType='application/json'
                )
                print(f"📦 Archived {len(logs)} logs to s3://{s3_bucket}/{s3_key}")
            except Exception as e:
                print(f"⚠️ S3 Archive failed: {e}")

        if not logs:
            return {"statusCode": 200, "body": "No logs"}

        # ================= PER-COMPANY ANALYSIS =================
        logs_by_company = defaultdict(list)
        for log in logs:
            cid = log.get('company_id', 'UNKNOWN')
            logs_by_company[cid].append(log)

        for cid, clogs in logs_by_company.items():
            print(f"[COMPANY] {cid}: {len(clogs)} logs received")

        hybrid_alerts = []
        rule_alerts = []

        for company_id, company_logs in logs_by_company.items():
            # Rule-based detection (per company)
            rule_alerts.extend(detect_multiple_failed_logins(company_logs))
            rule_alerts.extend(detect_password_spray(company_logs))
            rule_alerts.extend(detect_velocity_abuse(company_logs))
            rule_alerts.extend(detect_impossible_travel(company_logs))

            # ML-based detection (per company)
            if len(company_logs) < 3:
                print(f"[{company_id}] Only {len(company_logs)} logs — skipping ML, running rules only")
                continue

            features, usernames, _, ips = extract_features(company_logs)
            print(f"[{company_id}] Calling ML Lambda with {len(features)} feature vectors")

            try:
                # --- TASK 4: FAIL-SAFE ML CALL ---
                response = lambda_client.invoke(
                    FunctionName='ml-lambda-function',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({"features": features, "company_id": company_id})
                )
                
                payload = json.loads(response['Payload'].read())
                
                # --- TASK 3: ROBUST PARSING ---
                if 'body' not in payload:
                    print(f"⚠️ [{company_id}] ML returned invalid response format: {payload}")
                    raise Exception("Invalid ML response body")
                    
                body = json.loads(payload['body'])
                scores = body.get('scores', [0] * len(features))
                predictions = body.get('predictions', [1] * len(features))
                
            except Exception as e:
                print(f"⚠️ [{company_id}] ML failed, using fallback (normal): {e}")
                scores = [0.0] * len(features)
                predictions = [1] * len(features)

            print(f"[{company_id}] ML Scores: {scores}")

            for i in range(len(features)):
                risk_score, level, reasons = compute_risk(features[i], predictions[i])

                # Alerts must ONLY be generated when: ML anomaly OR risk_score > 40
                if predictions[i] == -1 or risk_score > 40:
                    lat, lon, country = get_real_geo(ips[i])
                    hybrid_alerts.append({
                        'id': str(uuid.uuid4()),
                        'user_id': usernames[i],
                        'company_id': company_id,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'ip': ips[i],
                        'latitude': Decimal(str(lat)),
                        'longitude': Decimal(str(lon)),
                        'country': country,
                        'threat_flag': True,
                        'alert_type': 'HYBRID_ANALYSIS',
                        'risk_level': level,
                        'status': 'ACTIVE',
                        'count': Decimal('1'),
                        'risk_score': Decimal(str(risk_score)),
                        'ml_score': Decimal(str(round(scores[i], 2))),
                        'reasons': reasons
                    })

        # ================= STORE =================
        processed_items = []

        for log in logs:
            processed_items.append({
                'log_id': str(uuid.uuid4()),          # ✅ PRIMARY KEY — required
                'user_id': log.get('user_id', 'UNKNOWN'),
                'timestamp': log.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                'ip': log.get('ip', 'UNKNOWN'),
                'company_id': log.get('company_id', 'UNKNOWN'),  # ✅ TENANT TAG
                'log_source': log.get('log_source', 'Unknown'),
                'threat_flag': False,
                'login_status': log.get('status', 'unknown')
            })

        print(f"🧾 DB_DEBUG - Writing {len(processed_items)} logs with primary keys to DynamoDB (Sample):")
        print(json.dumps(processed_items[:2], default=str))

        batch_write_to_dynamodb(logs_table, processed_items)
        all_alerts = hybrid_alerts + rule_alerts
        for al in all_alerts:
            al['log_sources'] = list(user_sources.get(al['user_id'], ['Custom_Auth_API']))
            
        print(f"🧾 DB_DEBUG - Writing {len(all_alerts)} alerts with tenant tags to DynamoDB (Sample):")
        print(json.dumps(all_alerts[:2], default=str))
        
        batch_write_to_dynamodb(alerts_table, all_alerts)

        # ================= SOAR ORCHESTRATION =================
        for alert in all_alerts:
            if alert.get('risk_level') in ['HIGH', 'CRITICAL']:
                company_id = alert.get('company_id', 'UNKNOWN')
                print(f"🔥 SOAR Triggered: Sending Alert for {alert.get('user_id')} at company {company_id}")
                
                # Fetch company contact email
                contact = get_company_contact(dynamodb, company_id)
                if contact and contact.get('email'):
                    send_email_alert(alert, contact['email'])
                else:
                    print(f"⚠️ No email contact for {company_id}, skipping SOAR.")

        print(f"✅ Stored {len(hybrid_alerts) + len(rule_alerts)} total alerts")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "logs": len(logs),
                "alerts": len(hybrid_alerts) + len(rule_alerts)
            })
        }

    except Exception as e:
        print(f"❌ Critical error: {e}")
        import traceback
        traceback.print_exc()
        return {"statusCode": 500, "body": str(e)}
