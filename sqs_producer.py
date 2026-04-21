import boto3
import json
import random
import time
from datetime import datetime, timedelta
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

time_offset = 0

def build_log(username, ip, status, company_id):
    global time_offset
    dt = datetime.utcnow() + timedelta(microseconds=time_offset)
    time_offset += 1000  # Unique timestamp scaling
    return {
        "username": username,
        "ip": ip,
        "status": status,
        "timestamp": dt.isoformat() + 'Z',
        "log_source": "Custom_Auth_API",
        "company_id": company_id
    }

def generate_normal_log(company_id, company_config):
    user = random.choice(company_config['users'])
    ip = random.choice(company_config['normal_ips']) if random.random() < 0.8 else random.choice(company_config['attack_ip_pool'])
    status = "success" if random.random() < 0.9 else "failure"
    return [build_log(user, ip, status, company_id)]

def simulate_brute_force(company_id, company_config):
    user = random.choice(company_config['users'])
    ip = random.choice(company_config['attack_ip_pool'])
    return [build_log(user, ip, "failure", company_id) for _ in range(10)]

def simulate_password_spray(company_id, company_config):
    ip = random.choice(company_config['attack_ip_pool'])
    return [build_log(user, ip, "failure", company_id) for user in company_config['users']]

def simulate_credential_stuffing(company_id, company_config):
    user = random.choice(company_config['users'])
    logs = []
    for _ in range(8):
        status = random.choice(["success", "failure"]) if random.random() < 0.2 else "failure"
        ip = random.choice(company_config['attack_ip_pool'])
        logs.append(build_log(user, ip, status, company_id))
    return logs

def stream_logs(mode="mixed", target_company=None, dry_run=False):
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

    print(f"Starting advanced stream {'(DRY RUN)' if dry_run else ''} -> {SQS_QUEUE_URL} | Mode: {mode}")
    
    total_sent = 0
    attack_count = 0

    try:
        while True:
            company_id = target_company if target_company else random.choice(list(COMPANIES.keys()))
            comp_conf = COMPANIES[company_id]
            batch_logs = []
            
            is_attack = False

            if mode == "normal_only":
                batch_logs = generate_normal_log(company_id, comp_conf)
            elif mode == "attack_only":
                attack = random.choice(["brute_force", "password_spray", "credential_stuffing"])
                if attack == "brute_force": batch_logs = simulate_brute_force(company_id, comp_conf)
                elif attack == "password_spray": batch_logs = simulate_password_spray(company_id, comp_conf)
                else: batch_logs = simulate_credential_stuffing(company_id, comp_conf)
                is_attack = True
            else:
                # MIXED
                rand_val = random.random()
                if rand_val < 0.6:
                    batch_logs = generate_normal_log(company_id, comp_conf)
                elif rand_val < 0.8:
                    batch_logs = simulate_brute_force(company_id, comp_conf)
                    is_attack = True
                elif rand_val < 0.9:
                    batch_logs = simulate_password_spray(company_id, comp_conf)
                    is_attack = True
                else:
                    batch_logs = simulate_credential_stuffing(company_id, comp_conf)
                    is_attack = True

            if is_attack:
                attack_count += 1
                color = RED
            else:
                color = GREEN

            # Submit
            for log_dict in batch_logs:
                msg = json.dumps(log_dict)
                if not dry_run:
                    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=msg)
                total_sent += 1
                
                print(f"{color}-> Sent: {msg[:85]}...{RESET}")
                time.sleep(0.05) if not dry_run else time.sleep(0.01)

            if total_sent % 10 == 0 or total_sent > 10:
                print(f"{YELLOW}--- Sent {total_sent} logs | Companies active: {len(COMPANIES)} | Attacks simulated: {attack_count} ---{RESET}")
                
            time.sleep(1.5)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Stream stopped manually. Total logs transmitted: {total_sent}{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Multi-Tenant Cloud SIEM Log Producer')
    parser.add_argument('--mode', choices=['mixed', 'attack_only', 'normal_only'], default='mixed', help='Flow generation scheme')
    parser.add_argument('--company', type=str, help='Force target a specific company ID')
    parser.add_argument('--dry-run', action='store_true', help='Print logs locally without SQS ingestion')
    args = parser.parse_args()

    if args.company and args.company not in COMPANIES:
        print(f"{RED}Error: Company '{args.company}' not found in configuration!{RESET}")
        sys.exit(1)

    stream_logs(mode=args.mode, target_company=args.company, dry_run=args.dry_run)
