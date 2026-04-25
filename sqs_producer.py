import json
import random
import time
from datetime import datetime
import argparse
import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

# Colors for terminal output
RED = '\033[91m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RESET = '\033[0m'

# ⚙️ SIEM CONFIGURATION
SIEM_URL = os.getenv("SIEM_URL", "http://localhost:5000/api/ingest")
SIEM_API_KEY = os.getenv("SIEM_API_KEY")

if not SIEM_API_KEY:
    print(f"{RED}🛑 STOP! Missing required SIEM_API_KEY!{RESET}")
    print("Please ensure you registered on the dashboard and added your SIEM_API_KEY to your .env file.")
    sys.exit(1)

# Generic company network simulation
USERS = ["admin", "root", "dev_service", "billing_api", "employee_portal"]
NORMAL_IPS = ["192.168.1.5", "192.168.1.10", "10.0.0.50"]
ATTACK_IP_POOL = ["185.220.101.45", "91.108.4.1", "194.169.1.5", "203.0.113.99"]

def build_log(username, ip, status):
    dt = datetime.utcnow()
    return {
        "username": username,
        "ip": ip,
        "status": status,
        "timestamp": dt.isoformat() + 'Z',
        "log_source": "Custom_Auth_API"
        # Notice we don't send company_id here! The API securely assigns it based on the API Key.
    }

def generate_logs(mode="mixed", count=None):
    count = count or random.randint(5, 10)
    logs = []
    
    # Logic to determine if this specific batch is an attack
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
            user = random.choice(USERS)
            ip = random.choice(ATTACK_IP_POOL)
            status = "failure"
        else:
            # Generate normal log
            user = random.choice(USERS)
            ip = random.choice(NORMAL_IPS) if random.random() < 0.9 else random.choice(ATTACK_IP_POOL)
            status = "success" if random.random() < 0.95 else "failure"
        
        logs.append(build_log(user, ip, status))
    
    return logs, is_attack

def stream_logs(mode="mixed", dry_run=False):
    print(f"Starting Generic Client Agent {'(DRY RUN)' if dry_run else ''} -> {SIEM_URL} | Mode: {mode}")
    
    total_sent = 0

    try:
        while True:
            batch_logs, is_attack = generate_logs(mode=mode)
            color = RED if is_attack else GREEN
            print(f"{color}[CLIENT AGENT] → Sending batch of {len(batch_logs)} logs to SIEM{RESET}")
            
            if not dry_run:
                try:
                    response = requests.post(
                        SIEM_URL,
                        headers={"X-API-Key": SIEM_API_KEY, "Content-Type": "application/json"},
                        json=batch_logs,
                        timeout=5
                    )
                    if response.status_code == 200:
                        total_sent += len(batch_logs)
                    else:
                        print(f"{RED}Server Error ({response.status_code}): {response.text}{RESET}")
                except Exception as e:
                    print(f"{RED}Connection Failed: {e}{RESET}")
            else:
                for log in batch_logs:
                    print(log)
            
            # Control Flow: Wait before sending next batch
            wait_time = random.randint(3, 8)
            print(f"{YELLOW}--- Batch sent. Total sent: {total_sent} | Sleeping for {wait_time}s ---{RESET}")
            time.sleep(wait_time)

    except KeyboardInterrupt:
        print(f"\n{YELLOW}🛑 Stream stopped manually. Total logs transmitted: {total_sent}{RESET}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generic SIEM Client Agent')
    parser.add_argument('--mode', choices=['mixed', 'attack_only', 'normal_only'], default='mixed', help='Flow generation scheme')
    parser.add_argument('--dry-run', action='store_true', help='Print logs locally without sending to SIEM')
    args = parser.parse_args()

    stream_logs(mode=args.mode, dry_run=args.dry_run)
