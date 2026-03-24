import json
import boto3
from datetime import datetime

# AWS Clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# DynamoDB Tables (Week 4)
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')


def store_alert_in_dynamodb(username, ip, failed_attempts, timestamp, threat_flag=True):
    """Store detected anomaly/alert in DynamoDB"""
    try:
        ALERTS_TABLE.put_item(
            Item={
                'user_id': username,
                'timestamp': timestamp,
                'ip': ip,
                'threat_flag': threat_flag,
                'failed_attempts': failed_attempts,
                'alert_type': 'MULTIPLE_FAILED_LOGINS',
                'severity': 'HIGH' if failed_attempts >= 5 else 'MEDIUM',
                'status': 'ACTIVE'
            }
        )
        print(f"✅ Alert stored in DynamoDB: {username} from {ip}")
    except Exception as e:
        print(f"❌ Error storing alert: {e}")


def store_processed_log_in_dynamodb(log_entry, is_threat=False):
    """Store processed log entry in DynamoDB"""
    try:
        PROCESSED_LOGS_TABLE.put_item(
            Item={
                'user_id': log_entry.get('username'),
                'timestamp': log_entry.get('timestamp'),
                'ip': log_entry.get('ip'),
                'threat_flag': is_threat,
                'user_agent': log_entry.get('user_agent'),
                'login_status': log_entry.get('status'),
                'processed_at': datetime.utcnow().isoformat() + 'Z'
            }
        )
    except Exception as e:
        print(f"❌ Error storing processed log: {e}")


def lambda_handler(event, context):
    print("🚀 Lambda started processing - Week 4 DynamoDB Integration")

    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        print(f"Bucket: {bucket}")
        print(f"File: {key}")

        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        logs = []

        for line in content.splitlines():
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    print("Invalid log skipped")

        print(f"✅ Total logs parsed: {len(logs)}")

        # Store all processed logs in DynamoDB
        for log in logs:
            store_processed_log_in_dynamodb(log, is_threat=False)

        # 🚨 Anomaly Detection Rule 1: Multiple Failed Logins
        failed_count = {}

        for log in logs:
            if log.get("status") == "failure":
                user_key = (log.get("username"), log.get("ip"))
                failed_count[user_key] = failed_count.get(user_key, 0) + 1

        # Store alerts for detected threats in DynamoDB
        alerts_count = 0
        for (username, ip), count in failed_count.items():
            if count >= 3:
                print("🚨 ALERT: Multiple failed logins detected!")
                print(f"User: {username}, IP: {ip}, Attempts: {count}")
                
                timestamp = datetime.utcnow().isoformat() + 'Z'
                store_alert_in_dynamodb(username, ip, count, timestamp, threat_flag=True)
                alerts_count += 1

        print(f"📊 Processing complete. Logs stored: {len(logs)}, Alerts detected: {alerts_count}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "total_logs": len(logs),
                "alerts_detected": alerts_count,
                "message": "Week 4 DynamoDB integration successful"
            })
        }

    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }