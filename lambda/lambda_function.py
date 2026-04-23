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

# AWS Clients
s3 = boto3.client('s3')
lambda_client = boto3.client('lambda')

# Cross-account role ARN
CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::502881461360:role/DynamoDBCrossAccountRole"

# 🔐 Assume role and get DynamoDB access
def get_dynamodb():
    sts_client = boto3.client('sts')

    assumed_role = sts_client.assume_role(
        RoleArn=CROSS_ACCOUNT_ROLE_ARN,
        RoleSessionName="LambdaSession"
    )

    credentials = assumed_role['Credentials']

    dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

    return dynamodb

# =========================
# CONFIG & ENV VARS
# =========================
# Required Lambda Environment Variables:
# SLACK_WEBHOOK_URL — Slack incoming webhook
# CROSS_ACCOUNT_ROLE_ARN — IAM role for DynamoDB cross-account access
# DEFAULT_COMPANY_ID — fallback company_id for logs without one
# SES_SENDER_EMAIL — verified SES sender email
# DASHBOARD_URL — URL of the React dashboard for email links

FAILED_LOGIN_THRESHOLD = 3
PASSWORD_SPRAY_THRESHOLD = 5
MAX_LOGINS_PER_MINUTE = 10

# Get Slack Webhook from environment variable (Security Best Practice)
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
DEFAULT_COMPANY_ID = "TECH_007"
SES_SENDER_EMAIL = "security@example.com"
DASHBOARD_URL = "http://localhost:5173"
# =========================
# UTILS
# =========================
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
            if 'username' in log_dict and 'ip' in log_dict and 'status' in log_dict:
                log_dict['log_source'] = log_dict.get('log_source', 'Custom_Auth_API')
                return log_dict
            if 'userIdentity' in log_dict and 'eventName' in log_dict:
                return {
                    'username': log_dict['userIdentity'].get('userName', 'UNKNOWN'), 'ip': log_dict.get('sourceIPAddress', 'UNKNOWN'),
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
                'username': d['user'] if d['user'] != '-' else 'UNKNOWN', 'ip': d['ip'],
                'status': 'success' if d['status'].startswith('2') or d['status'].startswith('3') else 'failure',
                'timestamp': datetime.utcnow().isoformat() + 'Z', 'log_source': 'Apache_WebServer',
                'company_id': 'UNKNOWN'
            }
        syslog_match = re.search(r'SRC=(?P<ip>\S+).*?USER=(?P<user>\S+).*?STATUS=(?P<status>success|failure|failed|accepted)', line, re.IGNORECASE)
        if syslog_match:
            d = syslog_match.groupdict()
            return {
                'username': d['user'], 'ip': d['ip'],
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
        return parsed

def send_slack_alert(alert):
    if not SLACK_WEBHOOK_URL or "YOUR_DUMMY_URL_HERE" in SLACK_WEBHOOK_URL:
        print("⚠️ Slack webhook not configured. Skipping alert.")
        return

    try:
        payload = {
            "text": f"🚨 *CRITICAL SECURITY ALERT* 🚨\n"
                    f"*Company:* `{alert.get('company_id', 'UNKNOWN')}`\n"
                    f"*User:* `{alert.get('user_id', 'UNKNOWN')}`\n"
                    f"*IP:* `{alert.get('ip', 'UNKNOWN')}`\n"
                    f"*Risk Level:* {alert.get('risk_level')}\n"
                    f"*Risk Score:* {alert.get('risk_score', 'N/A')}\n"
                    f"*Attack Pattern:* {', '.join(alert.get('reasons', []))}"
        }
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=3)
        print("✅ Slack alert dispatched")
    except Exception as e:
        print(f"❌ Slack error: {e}")

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
            key = (log.get('username', 'UNKNOWN'), log.get('ip', 'UNKNOWN'))
            failed_count[key] += 1
            ip_company[key] = log.get('company_id', 'UNKNOWN')

    for (user, ip), count in failed_count.items():
        if count >= FAILED_LOGIN_THRESHOLD:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
                'company_id': ip_company.get((user, ip), 'UNKNOWN'),  # ✅
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': ip,
                'alert_type': 'MULTIPLE_FAILED_LOGINS',
                'count': count,
                'risk_score': 60,
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
            ip_users[ip].add(log.get('username', 'UNKNOWN'))
            ip_company[ip] = log.get('company_id', 'UNKNOWN')

    for ip, users in ip_users.items():
        if len(users) >= PASSWORD_SPRAY_THRESHOLD:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': 'SYSTEM',
                'company_id': ip_company.get(ip, 'UNKNOWN'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': ip,
                'alert_type': 'PASSWORD_SPRAY',
                'count': len(users),
                'risk_score': 90,
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
            ts = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
            user = log.get('username', 'UNKNOWN')
            user_times[user].append(ts)
            user_company[user] = log.get('company_id', 'UNKNOWN')
        except Exception:
            continue

    for user, times in user_times.items():
        if len(times) > MAX_LOGINS_PER_MINUTE:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
                'company_id': user_company.get(user, 'UNKNOWN'),
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'ip': 'UNKNOWN',
                'alert_type': 'VELOCITY_ABUSE',
                'count': len(times),
                'risk_score': 85,
                'risk_level': 'HIGH',
                'reasons': ['rule_based_velocity_abuse']
            })

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
                    hybrid_alerts.append({
                        'id': str(uuid.uuid4()),
                        'user_id': usernames[i],
                        'company_id': company_id,
                        'timestamp': datetime.utcnow().isoformat() + 'Z',
                        'ip': ips[i],
                        'threat_flag': True,
                        'alert_type': 'HYBRID_ANALYSIS',
                        'risk_level': level,
                        'status': 'ACTIVE',
                        'count': 1,
                        'risk_score': risk_score,
                        'ml_score': Decimal(str(round(scores[i], 2))),
                        'reasons': reasons
                    })

        # ================= STORE =================
        processed_items = []

        for log in logs:
            processed_items.append({
                'log_id': str(uuid.uuid4()),          # ✅ PRIMARY KEY — required
                'user_id': log.get('username', 'UNKNOWN'),
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
        company_high_alert_counts = defaultdict(int)

        for alert in all_alerts:
            if alert.get('risk_level') in ['HIGH', 'CRITICAL']:
                print(f"🔥 SOAR Triggered: Sending Alert for {alert.get('user_id')} at company {alert.get('company_id')}")
                send_slack_alert(alert)
                company_id = alert.get('company_id', 'UNKNOWN')
                if company_id != 'UNKNOWN':
                    company_high_alert_counts[company_id] += 1
                # Here we could also push the IP to a Banned_IPs DynamoDB table.

        for company_id, count in company_high_alert_counts.items():
            send_company_email_alert(dynamodb, company_id, count)

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
