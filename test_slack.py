import urllib.request
import json

# =====================================================================
# ONLY PASTE YOUR URL HERE TO TEST IT LOCALLY BEFORE DEPLOYING!
SLACK_WEBHOOK_URL = "https://hooks.slack.com/services/YOUR_DUMMY_URL_HERE"
# =====================================================================

def test_slack_webhook():
    if "YOUR_DUMMY_URL" in SLACK_WEBHOOK_URL:
        print("❌ You need to paste your Slack Webhook URL into the script first!")
        return
        
    print("🚀 Firing a mock CRITICAL alert to Slack...")
    
    mock_alert_payload = {
        "text": "🚨 *CRITICAL SECURITY ALERT (TEST)* 🚨\n"
                "*User:* `admin`\n"
                "*IP:* `194.169.1.5`\n"
                "*Type:* `HYBRID_ANALYSIS`\n"
                "*Risk Score:* `98`\n"
                "*Reasons:* `multiple_failed_attempts, ml_anomaly`\n\n"
                "_This is a test confirming that the SIEM SOAR pipeline successfully reached the SecOps Team!_"
    }
    
    try:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps(mock_alert_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        urllib.request.urlopen(req, timeout=5)
        print("✅ SUCCESS! Check your Slack channel; the message should have arrived instantly!")
    except Exception as e:
        print(f"❌ Failed to send Slack alert: {e}")

if __name__ == "__main__":
    test_slack_webhook()
