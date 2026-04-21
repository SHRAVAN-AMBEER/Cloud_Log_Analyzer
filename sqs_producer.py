import boto3
import json
import random
import time
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

# ⚙️ AWS CONFIGURATION
# Secrets are loaded dynamically from the .env file!
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-east-1"
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Connect to SQS remotely
try:
    sqs = boto3.client(
        'sqs',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
except Exception as e:
    print(f"Failed to initialize boto3 client. Did you install boto3? {e}")
    exit(1)

def generate_mock_log():
    # Force Password Spray attack (1 IP guessing multiple usernames) to trigger native CRITICAL rule!
    users = ["admin", "root", "dev_service", "hospital_api", "system_bot", "db_admin", "marketing_api"]
    user = random.choice(users)
    ip = "194.169.1.5" # Simulated Moscow IP
    status = "failure" 
    
    # Randomly select a format to prove the Universal Parser works
    format_type = random.choice(["JSON", "APACHE"])
    
    timestamp = datetime.utcnow().isoformat() + 'Z'

    if format_type == "JSON":
        return json.dumps({
            "username": user,
            "ip": ip,
            "status": status,
            "timestamp": timestamp,
            "log_source": "Custom_Auth_API"
        })
    else:
        status_code = "200" if status == "success" else "401"
        return f"{ip} - {user} [{timestamp}] \"GET /login HTTP/1.1\" {status_code}"


def stream_logs():
    if "YOUR_FRIENDS" in AWS_ACCESS_KEY_ID:
        print("🛑 STOP! You need to paste the AWS Credentials and Queue URL from your friend first!")
        return

    print(f"Starting Real-Time SIEM Log Stream to {SQS_QUEUE_URL}...")
    
    try:
        while True:
            log_body = generate_mock_log()
            
            response = sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=log_body
            )
            
            print(f"-Sent Event: {log_body[:60]}... -> MessageId: {response['MessageId']}")
            
            # Send rapidly to ensure SQS groups them into batches of 10 for Lambda!
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stream stopped manually.")
    except Exception as e:
        print(f"\n❌ Error streaming to SQS: {e}")

if __name__ == "__main__":
    stream_logs()
