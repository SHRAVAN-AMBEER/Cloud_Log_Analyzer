"""
Feature extraction utilities for ML model in Lambda
Extracts features from logs for anomaly score calculation
"""

import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

FEATURES = ['login_hour', 'failed_attempts', 'ip_count', 'failure_ratio']

def extract_user_features(logs, username):
    """
    Extract features for a specific user from logs
    Returns: feature vector [login_hour, failed_attempts, ip_count, failure_ratio]
    """
    user_logs = [log for log in logs if log.get('username') == username]
    
    if not user_logs:
        return np.zeros(len(FEATURES))
    
    features = np.zeros(len(FEATURES))
    
    # Feature 0: login_hour (hour of day, normalized to 0-24)
    hours = []
    for log in user_logs:
        try:
            ts = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
            hours.append(ts.hour)
        except (ValueError, AttributeError):
            pass
    if hours:
        features[0] = np.mean(hours)
    
    # Feature 1: failed_attempts (raw count)
    failed = sum(1 for log in user_logs if log.get('status') == 'failure')
    features[1] = float(failed)
    
    # Feature 2: ip_count (number of unique IPs)
    unique_ips = len(set(log.get('ip', 'UNKNOWN') for log in user_logs if log.get('ip')))
    features[2] = float(unique_ips)
    
    # Feature 3: failure_ratio (failed / total)
    total = len(user_logs)
    if total > 0:
        features[3] = failed / total
    else:
        features[3] = 0.0
    
    return features

def extract_all_user_features(logs):
    """
    Extract features for all users in logs
    Returns: dict of {username: feature_vector}
    """
    users = set(log.get('username', 'UNKNOWN') for log in logs)
    
    user_features = {}
    for username in users:
        user_features[username] = extract_user_features(logs, username)
    
    return user_features

def calculate_rule_based_score(alerts_for_user):
    """
    Calculate rule-based anomaly score (Sr) from alerts
    Converts rule-based detections to a normalized score: [-1, 1]
    
    - 0 alerts: Sr = -1 (normal)
    - 1-2 alerts: Sr = -0.5 (slightly suspicious)
    - 3+ alerts: Sr = 0.5+ (suspicious to critical)
    """
    alert_count = len(alerts_for_user)
    
    if alert_count == 0:
        return -1.0  # Strongly normal
    elif alert_count == 1:
        return -0.5  # Slightly suspicious
    elif alert_count == 2:
        return 0.0   # Neutral
    elif alert_count >= 3:
        # More alerts = higher score (up to 1.0)
        return min(0.5 + (alert_count - 3) * 0.25, 1.0)
    
    return 0.0

def calculate_hybrid_score(rule_score, ml_score, alpha=0.6):
    """
    Calculate hybrid anomaly score
    Sh = alpha * Sr + (1 - alpha) * Sa
    
    Args:
        rule_score (float): Rule-based anomaly score [-1, 1]
        ml_score (float): ML anomaly score (decision_function output, typically [-1, 1])
        alpha (float): Weight for rule-based score (default 0.6 = 60% rules, 40% ML)
    
    Returns:
        float: Hybrid score in range [-1, 1]
    """
    hybrid = alpha * rule_score + (1 - alpha) * ml_score
    return np.clip(hybrid, -1.0, 1.0)

def convert_hybrid_to_risk_score(hybrid_score):
    """
    Convert hybrid score [-1, 1] to risk score [0, 100]
    risk_score = int((Sh + 1) * 50)
    
    -1.0 → 0 (lowest risk)
     0.0 → 50 (medium risk)
     1.0 → 100 (highest risk)
    """
    return int((hybrid_score + 1) * 50)

def get_risk_level(risk_score):
    """
    Determine risk level from risk score
    """
    if risk_score < 30:
        return 'LOW'
    elif risk_score < 60:
        return 'MEDIUM'
    elif risk_score < 85:
        return 'HIGH'
    else:
        return 'CRITICAL'
