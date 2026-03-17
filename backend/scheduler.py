import time
import shutil
import schedule
from pathlib import Path
from datetime import datetime, UTC

from s3_upload import upload_auth_logs

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
CURRENT_LOG = LOGS_DIR / "auth_logs.jsonl"


def rotate_and_upload():
    if not CURRENT_LOG.exists():
        print("No logs found.")
        return

    if CURRENT_LOG.stat().st_size == 0:
        print("Log file empty.")
        return

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    rotated_file = LOGS_DIR / f"auth_logs_{timestamp}.jsonl"

    shutil.copy(CURRENT_LOG, rotated_file)

    print(f"Created batch file: {rotated_file}")

    try:
        upload_auth_logs(rotated_file)
        print("Upload complete")

        # clear main log file
        open(CURRENT_LOG, "w").close()

    except Exception as e:
        print("Upload failed:", e)


schedule.every(1).minutes.do(rotate_and_upload)

print("✅ Scheduler started... running every 1 minute")

while True:
    schedule.run_pending()
    time.sleep(1)