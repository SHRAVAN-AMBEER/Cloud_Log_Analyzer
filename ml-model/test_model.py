import joblib

model = joblib.load("model.joblib")

# Normal behavior
normal = [[10, 1, 1, 0.1]]

# Abnormal behavior
anomaly = [[2, 5, 6, 0.9]]

print("Normal Prediction:", model.predict(normal))
print("Anomaly Prediction:", model.predict(anomaly))