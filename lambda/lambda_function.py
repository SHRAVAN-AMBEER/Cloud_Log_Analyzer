import json
import boto3
from datetime import datetime
from collections import defaultdict
from botocore.exceptions import ClientError
from decimal import Decimal
import uuid

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
# CONFIG
# =========================
FAILED_LOGIN_THRESHOLD = 3
PASSWORD_SPRAY_THRESHOLD = 5
MAX_LOGINS_PER_MINUTE = 10

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

def validate_log_entry(log):
    required_fields = ['username', 'timestamp', 'ip', 'status']
    return all(log.get(field) for field in required_fields)


# =========================
# RULE DETECTION
# =========================
def detect_multiple_failed_logins(logs):
    alerts = []
    failed_count = defaultdict(int)

    for log in logs:
        if log.get('status') == 'failure':
            key = (log['username'], log['ip'])
            failed_count[key] += 1

    for (user, ip), count in failed_count.items():
        if count >= FAILED_LOGIN_THRESHOLD:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
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

    for log in logs:
        if log.get('status') == 'failure':
            ip_users[log['ip']].add(log['username'])

    for ip, users in ip_users.items():
        if len(users) >= PASSWORD_SPRAY_THRESHOLD:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': 'SYSTEM',
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

    for log in logs:
        try:
            ts = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
            user_times[log['username']].append(ts)
        except:
            continue

    for user, times in user_times.items():
        if len(times) > MAX_LOGINS_PER_MINUTE:
            alerts.append({
                'id': str(uuid.uuid4()),
                'user_id': user,
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
    user_data = defaultdict(list)

    for log in logs:
        user_data[log['username']].append(log)

    features = []
    usernames = []

    for user, entries in user_data.items():
        total = len(entries)
        failed = sum(1 for e in entries if e['status'] == 'failure')
        ips = set(e['ip'] for e in entries)

        latest = max(entries, key=lambda x: x['timestamp'])
        hour = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00')).hour

        features.append([hour, failed, len(ips), failed / total if total else 0])
        usernames.append(user)

    return features, usernames


# =========================
# HYBRID SCORING
# =========================
def compute_risk(feature, ml_score):
    login_hour, failed_attempts, ip_count, failure_ratio = feature

    # Rule Score
    Sr = 0
    if failed_attempts > 3:
        Sr += 0.4
    if failure_ratio > 0.5:
        Sr += 0.3
    if ip_count > 3:
        Sr += 0.3

    # ML Score
    Sa = -ml_score
    Sa = max(0, min(1, Sa))

    # Final Score
    alpha = 0.6
    Sh = alpha * Sr + (1 - alpha) * Sa

    risk_score = int(Sh * 100)

    if risk_score < 30:
        level = "LOW"
    elif risk_score < 70:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return risk_score, level, Sr, Sa


# =========================
# EXPLANATION
# =========================
def generate_explanation(feature, Sa):
    reasons = []
    login_hour, failed_attempts, ip_count, failure_ratio = feature

    if login_hour < 6 or login_hour > 22:
        reasons.append("unusual_login_time")

    if failure_ratio > 0.5:
        reasons.append("high_failure_rate")

    if ip_count > 3:
        reasons.append("multiple_ips")

    if failed_attempts > 5:
        reasons.append("multiple_failed_attempts")

    if Sa > 0.5:
        reasons.append("ml_anomaly")

    if not reasons:
        reasons.append("normal_behavior")

    return reasons


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
            return {"statusCode": 400, "body": json.dumps({"error": "No S3 records in event"})}

        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        logs = []
        for line in content.splitlines():
            try:
                log = json.loads(line)
                if validate_log_entry(log):
                    logs.append(log)
            except:
                continue

        print(f"✅ Parsed {len(logs)} logs")

        if not logs:
            return {"statusCode": 200, "body": "No logs"}

        # ================= ML CALL =================
        features, usernames = extract_features(logs)
        hybrid_alerts = []
        
        if features:
            print("🔥 CALLING ML LAMBDA NOW 🔥")
            response = lambda_client.invoke(
                FunctionName='ml-lambda-function',
                InvocationType='RequestResponse',
                Payload=json.dumps({"features": features})
            )

            result = json.loads(response['Payload'].read())
            body = json.loads(result['body'])

            scores = body['scores']

            for i in range(len(features)):
                feature = features[i]
                ml_score = scores[i]

                risk_score, level, Sr, Sa = compute_risk(feature, ml_score)
                reasons = generate_explanation(feature, Sa)

                hybrid_alerts.append({
                    'id': str(uuid.uuid4()),   
                    'user_id': usernames[i],
                    'timestamp': datetime.utcnow().isoformat() + 'Z',
                    'ip': 'UNKNOWN',
                    'threat_flag': risk_score > 30,
                    'alert_type': 'HYBRID_ANALYSIS',
                    'risk_level': level,
                    'status': 'ACTIVE',
                    'count': 1,
                    'risk_score': risk_score,
                    'rule_score': Decimal(str(round(Sr, 2))),
                    'ml_score': Decimal(str(round(Sa, 2))),
                    'reasons': reasons
                })

        # ================= RULE ALERTS (OPTIONAL) =================
        rule_alerts = []
        rule_alerts.extend(detect_multiple_failed_logins(logs))
        rule_alerts.extend(detect_password_spray(logs))
        rule_alerts.extend(detect_velocity_abuse(logs))

        # ================= STORE =================
        processed_items = []

        for log in logs:
            processed_items.append({
                'user_id': log.get('username', 'UNKNOWN'),
                'timestamp': log.get('timestamp', datetime.utcnow().isoformat() + 'Z'),
                'ip': log.get('ip', 'UNKNOWN'),
                'threat_flag': False,
                'login_status': log.get('status', 'unknown')
            })

        batch_write_to_dynamodb(logs_table, processed_items)
        batch_write_to_dynamodb(alerts_table, hybrid_alerts + rule_alerts)

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
