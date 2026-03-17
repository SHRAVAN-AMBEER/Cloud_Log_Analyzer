import os
from datetime import datetime
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"

load_dotenv(BASE_DIR / ".env")

AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")


def get_s3_client():
    return boto3.client("s3", region_name=AWS_REGION)


def build_s3_key(prefix="raw-logs/auth"):
    now = datetime.utcnow()
    date_prefix = now.strftime("%Y/%m/%d")
    timestamp = now.strftime("%Y%m%dT%H%M%SZ")
    filename = f"auth_logs_{timestamp}.jsonl"
    return f"{prefix}/{date_prefix}/{filename}"


def upload_auth_logs(file_path=None):
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET_NAME not set.")

    if file_path:
        log_file = Path(file_path)
    else:
        log_file = LOGS_DIR / "auth_logs.jsonl"

    if not log_file.exists() or log_file.stat().st_size == 0:
        print("No logs to upload.")
        return

    s3_key = build_s3_key()
    s3_client = get_s3_client()

    try:
        s3_client.upload_file(str(log_file), S3_BUCKET, s3_key)
        print(f"Uploaded {log_file} to s3://{S3_BUCKET}/{s3_key}")

    except (BotoCoreError, ClientError) as e:
        print(f"Upload error: {e}")
        return

    # only rotate if direct upload (not scheduler)
    if file_path is None:
        backup_file = LOGS_DIR / f"auth_logs_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.jsonl"
        log_file.rename(backup_file)
        print(f"Rotated local log file to {backup_file}")