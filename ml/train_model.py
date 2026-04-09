import json
import pandas as pd
from sklearn.ensemble import IsolationForest
import pickle

from feature_engineering import extract_features

# Load logs
with open("sample_logs.json") as f:
    logs = json.load(f)

# Extract features
features = extract_features(logs)

df = pd.DataFrame(features)

print("📊 Features:\n", df)

# Select ML columns
X = df[["login_hour", "failed_attempts", "ip_count", "failure_ratio"]]

# Train model
model = IsolationForest(
    n_estimators=100,
    contamination=0.3,
    random_state=42
)

model.fit(X)

# Save model
with open("model.pkl", "wb") as f:
    pickle.dump(model, f)

print("✅ Model trained and saved as model.pkl")