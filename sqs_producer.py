import boto3
import json
import random
import time
from datetime import datetime, timedelta

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


time_offset = 0

def generate_mock_log(user=None, ip=None, status="failure"):
    global time_offset
    # Target IPs and usernames for dynamic mock logs
    users = ["admin", "root", "dev_service", "hospital_api", "system_bot", "db_admin", "marketing_api"]
    user = user or random.choice(users)
    ip = ip or "194.169.1.5"  # Simulated Moscow IP
    
    # Randomly select a format to prove the Universal Parser works
    format_type = random.choice(["JSON", "APACHE"])
    
    # Add an artificial microsecond offset to guarantee unique timestamps in tight loops
    dt = datetime.utcnow() + timedelta(microseconds=time_offset)
    time_offset += 1000  # Offset by 1ms per log
    timestamp = dt.isoformat() + 'Z'

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


def stream_burst(burst_size=15):
    """Send a burst of logs for one attack scenario to fill an SQS batch"""
    messages = []
    users = ["admin", "root", "dev_service", "hospital_api", "system_bot", "db_admin", "marketing_api"]
    ATTACK_IPS = ["194.169.1.5", "203.0.113.43", "45.22.19.112"]
    
    # Pick a random attack scenario
    scenario = random.choice(['normal', 'brute_force', 'password_spray'])
    
    if scenario == 'brute_force':
        # Same user, same IP, rapid failures — fill the batch
        user = random.choice(users)
        ip = random.choice(ATTACK_IPS)
        for _ in range(burst_size):
            messages.append(generate_mock_log(user=user, ip=ip, status='failure'))
            
    elif scenario == 'password_spray':
        # Different users, same IP, all failures
        ip = random.choice(ATTACK_IPS)
        for user in random.choices(users, k=burst_size):
            messages.append(generate_mock_log(user=user, ip=ip, status='failure'))
            
    else:
        # Normal mixed traffic
        for _ in range(burst_size):
            messages.append(generate_mock_log(user=random.choice(users), ip=f"10.0.0.{random.randint(1,255)}", status=random.choice(['success', 'failure'])))
            
    return messages


def stream_logs():
    if "YOUR_FRIENDS" in AWS_ACCESS_KEY_ID:
        print("🛑 STOP! You need to paste the AWS Credentials and Queue URL from your friend first!")
        return

    print(f"Starting burst log stream to {SQS_QUEUE_URL}...")
    
    try:
        while True:
            burst = stream_burst(burst_size=12)  # 12 logs → SQS batch of 10 + buffer
            for log_body in burst:
                response = sqs.send_message(
                    QueueUrl=SQS_QUEUE_URL,
                    MessageBody=log_body
                )
                print(f"→ Sent: {log_body[:50]}...")
                
                # 20 logs/sec — fast enough to fill batches but gives AWS time to queue it
                time.sleep(0.05)
                
            print(f"✅ Burst of {len(burst)} sent | Sleeping 2s before next burst")
            time.sleep(2)  # 2 second gap between bursts
            
    except KeyboardInterrupt:
        print("\n🛑 Stream stopped manually.")
    except Exception as e:
        print(f"\n❌ Error streaming to SQS: {e}")


if __name__ == "__main__":
    stream_logs()
