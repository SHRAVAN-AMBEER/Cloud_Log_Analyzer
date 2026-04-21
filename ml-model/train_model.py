import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

print("🚀 Training model...")

# Load dataset
df = pd.read_csv("baseline.csv")

# Create model
model = IsolationForest(
    contamination=0.05,  # IMPORTANT: realistic anomaly rate
    random_state=42
)

# Train ONLY on baseline (normal data)
model.fit(df.values)

# Save model
joblib.dump(model, "model.joblib")

print("✅ Model trained and saved as model.joblib")