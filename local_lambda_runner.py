import boto3
import json
import time
import uuid
import os
from datetime import datetime, timezone
from decimal import Decimal
from dotenv import load_dotenv

# Load all credentials from both .env files
load_dotenv('backend/.env')
load_dotenv('.env')

print("🚀 Starting Local Lambda Runner...")

# Initialize SQS (using sqs-sender-bot credentials)
sqs = boto3.client(
    'sqs',
    region_name='us-east-1',
    aws_access_key_id=os.getenv('SQS_AWS_ACCESS_KEY_ID', os.getenv('AWS_ACCESS_KEY_ID')),
    aws_secret_access_key=os.getenv('SQS_AWS_SECRET_ACCESS_KEY', os.getenv('AWS_SECRET_ACCESS_KEY'))
)
queue_url = os.getenv('SQS_QUEUE_URL')

# Initialize DynamoDB (using dynamodb-tester credentials)
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
alert_table = dynamodb.Table('SecurityAlerts')

print(f"📡 Polling SQS Queue: {queue_url}")

while True:
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=5
        )

        messages = response.get('Messages', [])
        if not messages:
            print(".", end="", flush=True)
            continue
            
        print(f"\n📥 Pulled {len(messages)} messages from SQS!")

        for msg in messages:
            try:
                log = json.loads(msg['Body'])
                company_id = log.get('company_id', 'UNKNOWN')
                
                print(f"⚙️ Processing log for company: {company_id} | Alert: {log.get('alert_type')}")
                
                # Simple detection logic for the local demo
                status = log.get('login_status') or log.get('status')
                is_failure = status == 'failure'
                
                # Basic alert type determination
                alert_type = log.get('alert_type')
                if not alert_type:
                    if is_failure:
                        alert_type = "MULTIPLE_FAILED_LOGINS"
                    else:
                        alert_type = "NORMAL_LOGIN"

                # Format into DynamoDB SecurityAlert
                alert_item = {
                    "id": str(uuid.uuid4()),
                    "company_id": company_id,
                    "user_id": log.get('username') or log.get('user_id') or 'unknown',
                    "risk_score": Decimal('95') if is_failure else Decimal('10'),
                    "risk_level": "CRITICAL" if is_failure else "LOW",
                    "alert_type": alert_type,
                    "reasons": ["Detected by Local Security Engine"],
                    "timestamp": datetime.now(timezone.utc).isoformat() + 'Z',
                    "ip": log.get('ip', '127.0.0.1'),
                    "latitude": Decimal(str(float(39.90 + (abs(hash(log.get('ip', ''))) % 10)))),
                    "longitude": Decimal(str(float(116.40 + (abs(hash(log.get('ip', ''))) % 10)))),
                    "country": "Simulated",
                    "log_sources": [log.get('log_source', 'Custom_API')]
                }
                
                # Write to DynamoDB
                alert_table.put_item(Item=alert_item)
                print(f"✅ Successfully saved alert to DynamoDB!")
                
                # Delete from SQS so it doesn't process again
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=msg['ReceiptHandle']
                )
                print("🗑️ Deleted message from SQS queue.")
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                
    except KeyboardInterrupt:
        print("\n🛑 Stopping runner.")
        break
    except Exception as e:
        print(f"\n⚠️ SQS Polling Error: {e}")
        time.sleep(5)
