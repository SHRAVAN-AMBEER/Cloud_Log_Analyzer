from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timezone
import json
from pathlib import Path
import boto3
from flask_cors import CORS
from boto3.dynamodb.conditions import Key, Attr
import requests
import random
import jwt
from datetime import timedelta
import io
import os
import uuid
import smtplib
import bcrypt
from email.mime.text import MIMEText
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
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-enterprise-key-123!")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "admin123")

def check_auth():
    """Validates JWT Token to simulate Multi-Tenant Isolation"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        try:
            return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return {"error": "Token has expired"}
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}
    return None

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json() or {}
    company_name = data.get("company_name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    industry = data.get("industry", "Unknown").strip().upper()
    
    if not company_name or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
        
    table = dynamodb.Table('Companies')
    try:
        existing = table.scan(FilterExpression=Attr('email').eq(email))
        if existing.get('Items'):
            return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        print(f"Error checking duplicate: {e}")
        
    rand_id = str(random.randint(100, 999))
    prefix = industry.replace(' ', '_').upper()[:10] if industry else "COMP"
    company_id = f"{prefix}_{rand_id}"
    
    try:
        while table.get_item(Key={'company_id': company_id}).get('Item'):
            rand_id = str(random.randint(100, 999))
            company_id = f"{prefix}_{rand_id}"
    except Exception:
        pass
        
    api_key = f"sk-live-{str(uuid.uuid4())}"
    hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    item = {
        "company_id": company_id,
        "company_name": company_name,
        "api_key": api_key,
        "email": email,
        "password_hash": hashed_pwd,
        "registered_at": datetime.now(timezone.utc).isoformat() + 'Z',
        "industry": industry,
        "alert_email_enabled": True,
        "status": "active"
    }
    
    try:
        table.put_item(Item=item)
        return jsonify({
            "message": "Registration successful",
            "company_id": company_id,
            "api_key": api_key
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    company_id = data.get("company_id", "").strip()
    password = data.get("password", "")
    api_key = data.get("api_key", "").strip()
    
    if data.get("username") == "superadmin":
        if password == SUPER_ADMIN_PASSWORD:
            token = jwt.encode({
                "role": "super_admin",
                "company_id": "ALL",
                "company_name": "Super Admin",
                "exp": datetime.now(timezone.utc) + timedelta(hours=24)
            }, JWT_SECRET, algorithm="HS256")
            return jsonify({"token": token, "role": "super_admin", "company_id": "ALL", "company_name": "Super Admin"}), 200
        return jsonify({"error": "Invalid super admin credentials"}), 401
    
    table = dynamodb.Table('Companies')
    
    if api_key:
        try:
            res = table.scan(FilterExpression=Attr('api_key').eq(api_key))
            items = res.get('Items', [])
            if not items:
                return jsonify({"error": "Invalid API key"}), 401
            company = items[0]
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    else:
        if not company_id or not password:
            return jsonify({"error": "Provide company_id and password, or api_key"}), 400
        try:
            res = table.get_item(Key={'company_id': company_id})
            company = res.get('Item')
            if not company:
                return jsonify({"error": "Invalid company_id"}), 401
            if not bcrypt.checkpw(password.encode('utf-8'), company['password_hash'].encode('utf-8')):
                return jsonify({"error": "Invalid password"}), 401
        except Exception as e:
            return jsonify({"error": str(e)}), 500
            
    if company.get('status') != 'active':
        return jsonify({"error": "Account suspended"}), 403

    try:
        table.update_item(
            Key={'company_id': company['company_id']},
            UpdateExpression="SET last_login = :val",
            ExpressionAttributeValues={':val': datetime.now(timezone.utc).isoformat() + 'Z'}
        )
    except Exception:
        pass
        
    token = jwt.encode({
        "role": "customer",
        "company_id": company['company_id'],
        "company_name": company.get('company_name', 'Unknown'),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }, JWT_SECRET, algorithm="HS256")
    
    return jsonify({
        "token": token,
        "role": "customer",
        "company_id": company['company_id'],
        "company_name": company.get('company_name', 'Unknown')
    }), 200

@app.route("/api/companies", methods=["GET"])
def api_companies():
    auth = check_auth()
    if not auth or "error" in auth:
        return jsonify({"error": auth.get("error") if auth else "Unauthorized"}), 401
    if auth.get("role") != "super_admin":
        return jsonify({"error": "Forbidden"}), 403
    try:
        table = dynamodb.Table('Companies')
        res = table.scan()
        companies = [{
            "company_id": i.get("company_id"),
            "company_name": i.get("company_name"),
            "industry": i.get("industry"),
            "registered_at": i.get("registered_at"),
            "status": i.get("status"),
            "last_login": i.get("last_login"),
            "alert_email_enabled": i.get("alert_email_enabled")
        } for i in res.get('Items', [])]
        return jsonify(companies), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/companies/<company_id>/send-alert-reminder", methods=["POST"])
def send_alert_reminder(company_id):
    auth = check_auth()
    if not auth or "error" in auth or auth.get("role") != "super_admin":
        return jsonify({"error": "Forbidden"}), 403
    try:
        table = dynamodb.Table('Companies')
        company = table.get_item(Key={'company_id': company_id}).get('Item')
        if not company:
            return jsonify({"error": "Company not found"}), 404
        recipient = company.get('email')
        if not recipient:
            return jsonify({"error": "Company has no registered email"}), 400
            
        sender = os.getenv("GMAIL_USER")
        email_password = os.getenv("GMAIL_PASS")
        if not sender or not email_password:
            return jsonify({"error": "SMTP credentials not configured on backend"}), 500
            
        msg = MIMEText("Your Cloud Log Analyzer dashboard has detected high/critical anomalies in the last 24 hours that have not been reviewed. Please log in immediately at your dashboard to review your threat intelligence.")
        msg["Subject"] = "⚠️ Security Alert: Unreviewed Anomalies in Your Dashboard"
        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, email_password)
            server.send_message(msg)
            
        table.update_item(
            Key={'company_id': company_id},
            UpdateExpression="SET last_alerted_at = :val",
            ExpressionAttributeValues={':val': datetime.now(timezone.utc).isoformat() + 'Z'}
        )
        return jsonify({"message": f"Alert reminder sent successfully to {recipient}"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
    except Exception:
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

@app.route("/alerts", methods=["GET"])
def get_alerts():
    auth_data = check_auth()
    if not auth_data or "error" in auth_data:
        return jsonify({"error": auth_data.get("error") if auth_data else "Unauthorized"}), 401
    
    company_id = auth_data['company_id']
    
    # Super admin can query any tenant
    if auth_data['role'] == 'super_admin':
        company_id = request.args.get('tenant', 'ALL')
    
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        if company_id == 'ALL':
            response = table.scan(Limit=500)
        else:
            # USE THE GSI — do NOT use scan()
            response = table.query(
                IndexName='company_id-timestamp-index',
                KeyConditionExpression=Key('company_id').eq(company_id),
                ScanIndexForward=False,
                Limit=500
            )
        alerts = [format_alert(i) for i in response.get('Items', [])]
        return jsonify(alerts)
    except Exception as e:
        print(f"DynamoDB error: {e}")
        return jsonify(get_mock_alerts()), 200

@app.route("/alerts/high", methods=["GET"])
def get_high_alerts():
    try:
        table = dynamodb.Table(ALERTS_TABLE_NAME)
        response = table.scan(
            FilterExpression=Attr('risk_level').is_in(['HIGH', 'CRITICAL'])
        )
        alerts = [format_alert(i) for i in response.get('Items', [])]
        return jsonify(alerts)
    except Exception:
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
        if target_tenant == 'ALL':
            response = table.scan(Limit=500)
        else:
            response = table.query(
                IndexName='company_id-timestamp-index',
                KeyConditionExpression=Key('company_id').eq(target_tenant),
                ScanIndexForward=False,
                Limit=500
            )
        filtered = [format_alert(i) for i in response.get('Items', [])]
    except Exception as e:
        print(f"PDF DynamoDB error: {e}")
        filtered = get_mock_alerts()

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