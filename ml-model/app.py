import json
import joblib
import numpy as np

print("🔥 ML MODEL INITIALIZING 🔥")
try:
    model = joblib.load("model.joblib")
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load model: {e}")
    model = None

def lambda_handler(event, context):
    print("🚀 ML Lambda invocation started")
    
    try:
        if model is None:
            raise Exception("Model not loaded")

        features = event.get("features", [])
        company_id = event.get("company_id", "UNKNOWN")

        if not features:
            print("⚠️ No features provided in event")
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No features provided"})
            }
        
        # Option A: No scaling for now (FAST FIX)
        X = np.array(features)
        
        print(f"[ML] Processing {len(features)} vectors for {company_id}")
        
        preds = model.predict(X)
        scores = model.decision_function(X)
        
        # Convert numpy types to native Python for JSON serialization
        preds_list = preds.tolist()
        scores_list = scores.tolist()
        
        print(f"[ML][{company_id}] Predictions: {preds_list}")
        print(f"[ML][{company_id}] Scores: {scores_list}")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "company_id": company_id,
                "predictions": preds_list,
                "scores": scores_list
            })
        }

    except Exception as e:
        print(f"❌ ML Lambda Error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e),
                "company_id": event.get("company_id", "UNKNOWN")
            })
        }
