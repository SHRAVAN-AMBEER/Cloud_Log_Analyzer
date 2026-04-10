"""
WEEK 6: ML Model Training Script
Trains Isolation Forest model for anomaly detection
Saves model to S3 for Lambda to load
"""

import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.ensemble import IsolationForest
import boto3
import os

# Features to extract
FEATURES = ['login_hour', 'failed_attempts', 'ip_count', 'failure_ratio']

def extract_features(logs):
    """
    Extract features from logs for ML model training
    Returns: list of feature vectors and list of usernames
    """
    user_features = {}
    
    # Group logs by user
    user_logs = defaultdict(list)
    for log in logs:
        username = log.get('username', 'UNKNOWN')
        user_logs[username].append(log)
    
    for username, user_log_list in user_logs.items():
        features = [0.0] * len(FEATURES)
        
        # Feature 1: login_hour (hour of day)
        hours = []
        for log in user_log_list:
            try:
                ts = datetime.fromisoformat(log.get('timestamp', '').replace('Z', '+00:00'))
                hours.append(ts.hour)
            except:
                pass
        if hours:
            features[0] = np.mean(hours)  # Average login hour
        
        # Feature 2: failed_attempts (count of failed logins)
        failed = sum(1 for log in user_log_list if log.get('status') == 'failure')
        features[1] = float(failed)
        
        # Feature 3: ip_count (number of unique IPs)
        unique_ips = len(set(log.get('ip', 'UNKNOWN') for log in user_log_list))
        features[2] = float(unique_ips)
        
        # Feature 4: failure_ratio (failed / total)
        total = len(user_log_list)
        if total > 0:
            features[3] = failed / total
        else:
            features[3] = 0.0
        
        user_features[username] = features
    
    return user_features

def generate_synthetic_training_data(num_samples=500):
    """
    Generate synthetic training data for ML model
    Mix of normal and anomalous patterns
    """
    logs = []
    users = [f'user{i}' for i in range(50)]
    ips = [f'192.168.1.{i}' for i in range(20)]
    
    # Normal logs (70% of data)
    for _ in range(int(num_samples * 0.7)):
        username = np.random.choice(users)
        ip = np.random.choice(ips[:5])  # Limited IP set for normal users
        status = np.random.choice(['success', 'failure'], p=[0.95, 0.05])
        ts = datetime.utcnow() - timedelta(days=np.random.randint(1, 30))
        
        logs.append({
            'username': username,
            'ip': ip,
            'status': status,
            'timestamp': ts.isoformat() + 'Z',
            'user_agent': 'Mozilla/5.0'
        })
    
    # Anomalous logs (30% of data)
    for _ in range(int(num_samples * 0.3)):
        username = np.random.choice(users)
        anomaly_type = np.random.choice(['many_ips', 'many_failures', 'unusual_time'])
        
        if anomaly_type == 'many_ips':
            # Same user, many different IPs
            ip = np.random.choice(ips)
            for _ in range(np.random.randint(5, 10)):
                logs.append({
                    'username': username,
                    'ip': np.random.choice(ips),
                    'status': 'success',
                    'timestamp': (datetime.utcnow() - timedelta(hours=np.random.randint(0, 24))).isoformat() + 'Z',
                    'user_agent': 'Mozilla/5.0'
                })
        elif anomaly_type == 'many_failures':
            # Many failed login attempts
            for _ in range(np.random.randint(5, 15)):
                logs.append({
                    'username': username,
                    'ip': np.random.choice(ips),
                    'status': 'failure',
                    'timestamp': (datetime.utcnow() - timedelta(minutes=np.random.randint(0, 30))).isoformat() + 'Z',
                    'user_agent': 'Mozilla/5.0'
                })
        else:
            # Unusual login times (late night/early morning)
            ts = datetime.utcnow().replace(hour=np.random.choice([23, 0, 1, 2, 3]))
            logs.append({
                'username': username,
                'ip': np.random.choice(ips),
                'status': 'success',
                'timestamp': ts.isoformat() + 'Z',
                'user_agent': 'Mozilla/5.0'
            })
    
    return logs

def train_isolation_forest(features_dict, contamination=0.15):
    """
    Train Isolation Forest model on extracted features
    Returns trained model
    """
    # Convert features dict to array
    X = np.array(list(features_dict.values()))
    
    print(f"📊 Training data shape: {X.shape}")
    print(f"📊 Feature names: {FEATURES}")
    
    # Train Isolation Forest
    model = IsolationForest(
        contamination=contamination,  # Expected proportion of anomalies
        random_state=42,
        n_estimators=100
    )
    
    model.fit(X)
    
    # Calculate anomaly scores for evaluation
    anomaly_scores = model.decision_function(X)
    predictions = model.predict(X)
    
    print(f"✅ Model trained successfully!")
    print(f"📊 Anomaly scores range: [{anomaly_scores.min():.3f}, {anomaly_scores.max():.3f}]")
    print(f"📊 Predicted anomalies: {sum(predictions == -1)} out of {len(predictions)}")
    
    return model

def save_model_to_s3(model, bucket_name='cloud-log-analyzer', key_name='ml_model/isolation_forest.pkl'):
    """
    Save trained model to S3
    """
    try:
        s3 = boto3.client('s3')
        
        # Serialize model
        model_bytes = pickle.dumps(model)
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=key_name,
            Body=model_bytes,
            ContentType='application/octet-stream',
            Metadata={'trained_at': datetime.utcnow().isoformat()}
        )
        
        print(f"✅ Model saved to s3://{bucket_name}/{key_name}")
        return True
    except Exception as e:
        print(f"❌ Error saving model to S3: {e}")
        return False

def save_model_locally(model, filepath='ml_model.pkl'):
    """
    Save trained model locally for testing
    """
    try:
        with open(filepath, 'wb') as f:
            pickle.dump(model, f)
        print(f"✅ Model saved locally to {filepath}")
        return True
    except Exception as e:
        print(f"❌ Error saving model locally: {e}")
        return False

def main():
    """Main training pipeline"""
    print("🚀 Starting ML Model Training Pipeline\n")
    
    # Step 1: Generate or load training data
    print("Step 1: Generating synthetic training data...")
    logs = generate_synthetic_training_data(num_samples=500)
    print(f"✅ Generated {len(logs)} log entries\n")
    
    # Step 2: Extract features
    print("Step 2: Extracting features...")
    features_dict = extract_features(logs)
    print(f"✅ Extracted features for {len(features_dict)} users")
    print(f"   Features: {FEATURES}\n")
    
    # Step 3: Train model
    print("Step 3: Training Isolation Forest model...")
    model = train_isolation_forest(features_dict, contamination=0.15)
    print()
    
    # Step 4: Save model
    print("Step 4: Saving model...")
    save_model_locally(model, 'ml_model.pkl')
    
    # Optional: Save to S3 (requires AWS credentials)
    # save_model_to_s3(model)
    
    print("\n✅ Training pipeline complete!")
    print("📝 Model saved as 'ml_model.pkl' - ready for Lambda")

if __name__ == '__main__':
    main()
