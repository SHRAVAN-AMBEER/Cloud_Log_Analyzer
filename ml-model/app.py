import json
import joblib
import numpy as np

print("🔥 REAL ML MODEL DEPLOYED 🔥")
model = joblib.load("model.joblib")

def lambda_handler(event, context):
    print("🚀 ML Lambda started")
    try:
        features = event.get("features", [])
        if not features:
            return {"statusCode": 400, "body": json.dumps("No features provided")}
        
        # We trained the model on raw Numpy arrays (Task 3 approach)
        # So we construct a pure Numpy array here for inference!
        X = np.array(features)
        
        preds = model.predict(X)
        scores = model.decision_function(X)
        
        print("Features:", X.tolist())
        print("Predictions:", preds.tolist())
        print("Scores:", scores.tolist())
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "predictions": preds.tolist(),
                "scores": scores.tolist()
            })
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"statusCode": 500, "body": str(e)}
