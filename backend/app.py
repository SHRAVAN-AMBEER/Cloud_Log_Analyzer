from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr

app = Flask(__name__)
CORS(app)

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


# INITIALIZE BOTO3
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ALERTS_TABLE_NAME = 'SecurityAlerts'

def format_alert(item):
    """Format alert to the STANDARDIZED API OUTPUT"""
    return {
        "user_id": item.get('user_id', 'UNKNOWN'),
        "risk_score": int(item.get('risk_score', 0)),
        "risk_level": item.get('risk_level', 'LOW'),
        "reasons": item.get('reasons', []),
        "timestamp": item.get('timestamp', '')
    }

@app.route("/alerts", methods=["GET"])
def get_alerts():
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan()
        alerts = [format_alert(i) for i in response.get('Items', [])]
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/alerts/high", methods=["GET"])
def get_high_alerts():
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan(
            FilterExpression=Attr('risk_level').is_in(['HIGH', 'CRITICAL'])
        )
        alerts = [format_alert(i) for i in response.get('Items', [])]
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/alerts/<user_id>", methods=["GET"])
def get_user_alerts(user_id):
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        )
        alerts = [format_alert(i) for i in response.get('Items', [])]
        return jsonify(alerts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)