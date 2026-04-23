import boto3
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime, timezone
import uuid
import bcrypt

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

def get_dynamodb():
    return boto3.resource(
        'dynamodb',
        region_name='us-east-1',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )

COMPANIES = {
    "HEALTHCARE_001": {"name": "Apollo MedNet", "industry": "Healthcare", "email": "security@apollomed.in"},
    "RETAIL_002": {"name": "ShopEasy India", "industry": "Retail", "email": "ops@shopeasy.co.in"},
    "FINANCE_003": {"name": "SecurePay Bank", "industry": "Finance", "email": "threats@securepay.com"},
    "EDUCATION_004": {"name": "LearnCloud University", "industry": "Education", "email": "it-security@learncloud.edu"},
    "LOGISTICS_005": {"name": "FastTrack Cargo", "industry": "Logistics", "email": "alert@fasttrack.com"},
    "INSURANCE_006": {"name": "SafeGuard Insurance", "industry": "Insurance", "email": "risk-team@safeguard.com"},
    "TECH_007": {"name": "DevOps Solutions", "industry": "Technology", "email": "security@devops.io"}
}

def seed():
    db = get_dynamodb()
    table = db.Table('Companies')
    
    print(f"Seeding {len(COMPANIES)} companies into 'Companies' table...")
    
    for cid, info in COMPANIES.items():
        # Check if already exists
        try:
            res = table.get_item(Key={'company_id': cid})
            if res.get('Item'):
                print(f"Company {cid} already exists. Skipping.")
                continue
        except Exception:
            pass
            
        hashed_pwd = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        item = {
            "company_id": cid,
            "company_name": info['name'],
            "api_key": f"sk-live-{str(uuid.uuid4())}",
            "email": info['email'],
            "password_hash": hashed_pwd,
            "registered_at": datetime.now(timezone.utc).isoformat() + 'Z',
            "industry": info['industry'],
            "alert_email_enabled": True,
            "status": "active"
        }
        table.put_item(Item=item)
        print(f"Registered {info['name']} ({cid})")

if __name__ == "__main__":
    seed()
