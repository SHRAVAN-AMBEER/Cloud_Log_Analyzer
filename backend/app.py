from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timezone
import json
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOGS_DIR / "auth_logs.jsonl"

VALID_USERNAME = "admin"
VALID_PASSWORD = "password123"


def get_client_ip():
    return request.remote_addr


@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    user_agent = request.headers.get("User-Agent", "")
    ip_address = get_client_ip()
    timestamp = datetime.now(timezone.utc).isoformat()

    status = "success" if username == VALID_USERNAME and password == VALID_PASSWORD else "failure"

    log_record = {
        "username": username,
        "ip": ip_address,
        "user_agent": user_agent,
        "timestamp": timestamp,
        "status": status,
    }

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_record) + "\n")

    if status == "success":
        return render_template("login.html", message="Login successful!", status=status)
    else:
        return render_template("login.html", message="Login failed", status=status), 401


if __name__ == "__main__":
    app.run(debug=True)