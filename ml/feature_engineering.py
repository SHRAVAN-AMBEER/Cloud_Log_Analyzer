from collections import defaultdict
from datetime import datetime

def extract_features(logs):
    user_data = defaultdict(list)

    for log in logs:
        user_data[log['username']].append(log)

    features = []

    for user, entries in user_data.items():
        total = len(entries)
        failed = sum(1 for e in entries if e['status'] == 'failure')
        ips = set(e['ip'] for e in entries)

        latest = max(entries, key=lambda x: x['timestamp'])
        hour = datetime.fromisoformat(latest['timestamp'].replace('Z', '+00:00')).hour

        features.append({
            "username": user,
            "login_hour": hour,
            "failed_attempts": failed,
            "ip_count": len(ips),
            "failure_ratio": failed / total if total else 0
        })

    return features 
