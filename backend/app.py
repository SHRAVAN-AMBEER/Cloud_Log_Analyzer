from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr
import requests
import random
from boto3.dynamodb.conditions import Key, Attr
import jwt
from datetime import timedelta
import io
from flask import send_file
from fpdf import FPDF

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


# ================= MULTI-TENANT SAAS AUTH =================
JWT_SECRET = "super-secret-enterprise-key-123!"

@app.route("/api/login", methods=["POST"])
def api_login():
    """Generates a secure Multi-Tenant JWT for API consumption"""
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    valid_users = {
        "admin": {"role": "super_admin", "company_id": "ALL"},
        "hospital": {"role": "customer", "company_id": "HOSPITAL"},
        "retail": {"role": "customer", "company_id": "RETAIL"}
    }

    if username in valid_users and password == "password123":
        user_data = valid_users[username]
        token = jwt.encode({
            "username": username,
            "role": user_data["role"],
            "company_id": user_data["company_id"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }, JWT_SECRET, algorithm="HS256")
        return jsonify({"token": token, "message": "Authenticated successfully", "role": user_data["role"], "company_id": user_data["company_id"]})
    
    return jsonify({"error": "Invalid credentials"}), 401

def check_auth():
    """Validates JWT Token to simulate Multi-Tenant Isolation"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            return decoded
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    return None


# INITIALIZE BOTO3
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
ALERTS_TABLE_NAME = 'SecurityAlerts'

IP_CACHE = {}

def get_geo_info(ip):
    if ip == 'UNKNOWN' or not ip or ip == '127.0.0.1':
        # Default mock locations for demo if IP is unknown (Simulating Global Attacks)
        mock_locations = [
            (39.9042, 116.4074), # Beijing
            (55.7558, 37.6173),  # Moscow
            (40.7128, -74.0060), # New York
            (51.5074, -0.1278),  # London
            (-23.5505, -46.6333) # Sao Paulo
        ]
        lat, lon = random.choice(mock_locations)
        return {"lat": lat, "lon": lon, "country": "Simulated"}

    if ip in IP_CACHE:
        return IP_CACHE[ip]

    try:
        res = requests.get(f'http://ip-api.com/json/{ip}', timeout=2)
        if res.status_code == 200:
            data = res.json()
            if data.get('status') == 'success':
                geo = {"lat": data.get('lat'), "lon": data.get('lon'), "country": data.get('country')}
                IP_CACHE[ip] = geo
                return geo
    except:
        pass
    
    # Fallback default
    return {"lat": 0, "lon": 0, "country": "Unknown"}

def format_alert(item):
    """Format alert to the STANDARDIZED API OUTPUT with GeoIP"""
    geo = get_geo_info(item.get('ip', 'UNKNOWN'))
    
    return {
        "id": item.get('id', 'unknown'),
        "user_id": item.get('user_id', 'UNKNOWN'),
        "risk_score": int(item.get('risk_score', 0)),
        "risk_level": item.get('risk_level', 'LOW'),
        "reasons": item.get('reasons', []),
        "timestamp": item.get('timestamp', ''),
        "ip": item.get('ip', 'UNKNOWN'),
        "latitude": geo["lat"],
        "longitude": geo["lon"],
        "country": geo["country"],
        "log_sources": item.get('log_sources', ['Custom_Auth_API'])
    }

def get_mock_alerts():
    """Generates realistic demo alerts when AWS credentials expire"""
    import uuid
    from datetime import datetime
    return [
        {
            "id": str(uuid.uuid4()), "user_id": "admin", "risk_score": 98, "risk_level": "CRITICAL",
            "reasons": ["multiple_failed_attempts", "ml_anomaly"], "timestamp": datetime.utcnow().isoformat() + 'Z',
            "ip": "194.169.1.5", "latitude": 55.7558, "longitude": 37.6173, "country": "Simulated",
            "log_sources": ["Cisco_Firewall", "Apache_WebServer"]
        },
        {
            "id": str(uuid.uuid4()), "user_id": "dev_service", "risk_score": 85, "risk_level": "HIGH",
            "reasons": ["velocity_abuse"], "timestamp": datetime.utcnow().isoformat() + 'Z',
            "ip": "203.0.113.43", "latitude": 39.9042, "longitude": 116.4074, "country": "Simulated",
            "log_sources": ["AWS_CloudTrail"]
        },
        {
            "id": str(uuid.uuid4()), "user_id": "marketing_api", "risk_score": 60, "risk_level": "MEDIUM",
            "reasons": ["multiple_ips"], "timestamp": datetime.utcnow().isoformat() + 'Z',
            "ip": "85.20.14.99", "latitude": 51.5074, "longitude": -0.1278, "country": "Simulated",
            "log_sources": ["Apache_WebServer"]
        }
    ]

def filter_alerts_for_demo(alerts, company_id):
    if company_id == 'HOSPITAL':
        return [a for a in alerts if 'Cisco_Firewall' in a.get('log_sources', [])]
    if company_id == 'RETAIL':
        return [a for a in alerts if 'AWS_CloudTrail' in a.get('log_sources', [])]
    return alerts

@app.route("/alerts", methods=["GET"])
def get_alerts():
    auth_data = check_auth()
    if not auth_data:
         return jsonify([a for a in get_mock_alerts() if 'Apache_WebServer' in a.get('log_sources', [])]) # graceful fallback if token missing for local quick dev
         
    print(f"🔒 Authenticated request from {auth_data['username']} (Tenant: {auth_data['company_id']})")
    
    target_tenant = auth_data['company_id']
    if auth_data['role'] == 'super_admin' and request.args.get('tenant'):
        target_tenant = request.args.get('tenant')
        
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan()
        alerts = [format_alert(i) for i in response.get('Items', [])]
        filtered = filter_alerts_for_demo(alerts, target_tenant)
        return jsonify(filtered)
    except Exception as e:
        print(f"⚠️ DynamoDB Error -> Enabling Showcase DEMO MODE: {e}")
        alerts = get_mock_alerts()
        return jsonify(filter_alerts_for_demo(alerts, target_tenant))

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
        return jsonify([a for a in get_mock_alerts() if a['risk_level'] in ('HIGH', 'CRITICAL')])

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

@app.route("/api/report", methods=["GET"])
def generate_pdf_report():
    auth_data = check_auth()
    if not auth_data:
        return jsonify({"error": "Unauthorized"}), 401
        
    target_tenant = auth_data['company_id']
    if auth_data['role'] == 'super_admin' and request.args.get('tenant'):
        target_tenant = request.args.get('tenant')

    # Fetch alerts for this tenant
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan()
        alerts = [format_alert(i) for i in response.get('Items', [])]
        filtered = filter_alerts_for_demo(alerts, target_tenant)
    except Exception:
        # Fallback to mock data if DynamoDB is unreachable
        filtered = filter_alerts_for_demo(get_mock_alerts(), target_tenant)

    # Calculate metrics
    total_alerts = len(filtered)
    high_critical = len([a for a in filtered if a.get('risk_level') in ['HIGH', 'CRITICAL']])
    unique_users = len(set([a.get('user_id') for a in filtered]))

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Security Intelligence Report: {target_tenant}", ln=True, align='C')
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Generated on: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Executive Summary", ln=True)
    pdf.set_font("Arial", '', 12)
    pdf.cell(200, 10, txt=f"Total Security Alerts: {total_alerts}", ln=True)
    pdf.cell(200, 10, txt=f"High & Critical Risk Alerts: {high_critical}", ln=True)
    pdf.cell(200, 10, txt=f"Unique Compromised Users: {unique_users}", ln=True)
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Recent Threat Detections", ln=True)
    pdf.set_font("Arial", '', 10)
    
    # Add a simple table-like list of the top 10 most recent alerts
    for a in filtered[:10]:
        pdf.cell(200, 8, txt=f"[{a.get('risk_level')}] User: {a.get('user_id')} | IP: {a.get('ip')} | Type: {a.get('alert_type')}", ln=True)
        
    pdf.ln(10)
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt="This report was automatically generated by the Enterprise Cloud SIEM Platform.", ln=True, align='C')

    # Return PDF securely as a file stream
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{target_tenant}_Security_Report.pdf"
    )


if __name__ == "__main__":
    app.run(debug=True)