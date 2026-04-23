import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

# Load dataset
try:
    df = pd.read_csv("dataset.csv")
except FileNotFoundError:
    print("❌ dataset.csv not found! Run generate_dataset.py first.")
    exit(1)

print(f"--- Training High-Sensitivity SIEM Anomaly Detector ---")
print(f"Total samples: {len(df)}")
print(f"Contamination level: 0.25")
print(f"Feature distribution:\n{df.describe().loc[['mean', 'std', 'min', 'max']]}")

# Train on raw features (Option A - No Scaling)
model = IsolationForest(
    n_estimators=200,
    contamination=0.25,
    random_state=42
)

# Train
model.fit(df.values)

# Save model
joblib.dump(model, "model.joblib")

print("✅ Model trained and saved as model.joblib")