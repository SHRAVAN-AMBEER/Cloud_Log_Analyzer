import boto3
import json
import random
import time
from datetime import datetime
import argparse
import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# ⚙️ AWS CONFIGURATION
AWS_ACCESS_KEY_ID = os.getenv("SQS_AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("SQS_AWS_SECRET_ACCESS_KEY")
AWS_REGION = "us-east-1"
SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")

# Validate Env Vars
if not AWS_ACCESS_KEY_ID or not AWS_SECRET_ACCESS_KEY or not SQS_QUEUE_URL:
    print(f"{RED}🛑 STOP! Missing required AWS environment variables!{RESET}")
    print("Please ensure SQS_AWS_ACCESS_KEY_ID, SQS_AWS_SECRET_ACCESS_KEY, and SQS_QUEUE_URL are in your .env")
    sys.exit(1)

COMPANIES = {
    "HEALTHCARE_001": {
        "name": "Apollo MedNet",
        "users": ["dr_sharma", "nurse_patel", "admin_rao", "lab_tech_01", "reception_desk"],
        "normal_ips": ["10.0.1.100", "10.0.1.101", "10.0.2.50"],
        "attack_ip_pool": ["185.220.101.45", "91.108.4.1", "194.169.1.5"],
        "industry": "Healthcare"
    },
    "RETAIL_002": {
        "name": "ShopEasy India",
        "users": ["store_mgr", "cashier_01", "cashier_02", "inventory_bot", "analytics_svc"],
        "normal_ips": ["192.168.10.5", "192.168.10.6"],
        "attack_ip_pool": ["203.0.113.99", "45.155.205.10"],
        "industry": "Retail"
    },
    "FINANCE_003": {
        "name": "SecurePay Bank",
        "users": ["teller_01", "risk_engine", "audit_bot", "branch_mgr", "loan_officer"],
        "normal_ips": ["172.16.0.10", "172.16.0.11"],
        "attack_ip_pool": ["91.219.239.1", "185.56.80.10", "103.21.244.0"],
        "industry": "Finance"
    },
    "EDUCATION_004": {
        "name": "LearnCloud University",
        "users": ["student_portal", "faculty_ravi", "library_sys", "exam_server", "admin_office"],
        "normal_ips": ["10.10.10.1", "10.10.10.2"],
        "attack_ip_pool": ["118.193.68.60", "196.52.43.1"],
        "industry": "Education"
    },
    "LOGISTICS_005": {
        "name": "FastTrack Cargo",
        "users": ["dispatch_01", "warehouse_bot", "driver_app", "customs_api", "tracking_svc"],
        "normal_ips": ["192.168.20.1", "192.168.20.2"],
        "attack_ip_pool": ["185.220.101.1", "94.102.49.190"],
        "industry": "Logistics"
    },
    "INSURANCE_006": {
        "name": "SafeGuard Insurance",
        "users": ["underwriter_01", "claims_bot", "agent_portal", "actuary_svc", "compliance_audit"],
        "normal_ips": ["10.20.0.5", "10.20.0.6"],
        "attack_ip_pool": ["185.107.80.50", "92.118.160.1"],
        "industry": "Insurance"
    },
    "TECH_007": {
        "name": "DevOps Solutions",
        "users": ["ci_pipeline", "deploy_bot", "monitoring_svc", "dev_john", "dev_priya"],
        "normal_ips": ["172.31.0.100", "172.31.0.101"],
        "attack_ip_pool": ["45.33.32.156", "198.20.69.74"],
        "industry": "Technology"
    }
}

def build_log(username, ip, status, company_id):
    assert company_id, "company_id must not be empty"
    dt = datetime.utcnow()
    return {
        "username": username,
        "ip": ip,
        "status": status,
        "timestamp": dt.isoformat() + 'Z',
        "log_source": "Custom_Auth_API",
        "company_id": company_id
    }

def generate_logs_for_company(company_id, mode="mixed", count=None):
    conf = COMPANIES[company_id]
    count = count or random.randint(5, 10)
    logs = []
    
    # Logic to determine if this specific company batch is an attack
    is_attack = False
    if mode == "attack_only":
        is_attack = True
    elif mode == "normal_only":
        is_attack = False
    else:
        is_attack = random.random() < 0.3 # 30% chance of attack in mixed mode
    
    for _ in range(count):
        if is_attack and random.random() < 0.7:
            # Generate attack-like log
            user = random.choice(conf['users'])
            ip = random.choice(conf['attack_ip_pool'])
            status = "failure"
        else:
            # Generate normal log
            user = random.choice(conf['users'])
            ip = random.choice(conf['normal_ips']) if random.random() < 0.9 else random.choice(conf['attack_ip_pool'])
            status = "success" if random.random() < 0.95 else "failure"
        
        logs.append(build_log(user, ip, status, company_id))
    
    return logs, is_attack

def stream_logs(mode="mixed", dry_run=False):
    try:
        if not dry_run:
            sqs = boto3.client(
                'sqs',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )
    except Exception as e:
        print(f"{RED}Failed to initialize boto3 client: {e}{RESET}")
        sys.exit(1)

    print(f"Starting structured multi-tenant stream {'(DRY RUN)' if dry_run else ''} -> {SQS_QUEUE_URL} | Mode: {mode}")
    
    total_sent = 0

    try:
        while True:
            # Structured Streaming: Iterate through each company
            for company_id in COMPANIES.keys():
                batch_logs, is_attack = generate_logs_for_company(company_id, mode=mode)
                
                # SQS Batch limit is 10
                for i in range(0, len(batch_logs), 10):
                    chunk = batch_logs[i:i+10]
                    
                    entries = [
                        {
                            "Id": str(j),
                            "MessageBody": json.dumps(log)
                        } for j, log in enumerate(chunk)
                    ]

                    color = RED if is_attack else GREEN
                    print(f"{color}[PRODUCER][COMPANY] {company_id} → Sending batch of {len(chunk)} logs{RESET}")
                    
                    if not dry_run:
                        sqs.send_message_batch(
                            QueueUrl=SQS_QUEUE_URL,
                            Entries=entries
                        )
                    
                    total_sent += len(chunk)
            
            # Control Flow: Wait between full sweeps
            wait_time = random.randint(5, 10)
            print(f"{YELLOW}--- Sweep complete. Total sent: {total_sent} | Sleeping for {wait_time}s ---{RESET}")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Stream stopped manually. Total logs transmitted: {total_sent}{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi-Tenant Cloud SIEM Log Producer')
    parser.add_argument('--mode', choices=['mixed', 'attack_only', 'normal_only'], default='mixed', help='Flow generation scheme')
    parser.add_argument('--dry-run', action='store_true', help='Print logs locally without SQS ingestion')
    args = parser.parse_args()

    stream_logs(mode=args.mode, dry_run=args.dry_run)
