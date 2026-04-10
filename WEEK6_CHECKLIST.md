# WEEK 6 IMPLEMENTATION CHECKLIST
## Shravan's ML Integration Tasks

---

## ✅ COMPLETED TASKS

### 1. Feature Extraction ✓
- [x] Created `feature_extraction.py` with 4-feature extraction
- [x] Integrated feature extraction in Lambda
- [x] Features: login_hour, failed_attempts, ip_count, failure_ratio

### 2. ML Model Training ✓
- [x] Created `train_ml_model.py` training script
- [x] Implements Isolation Forest model
- [x] Generates synthetic training data (500 samples)
- [x] Saves model as pickle file (~50KB)

### 3. ML Model Loading in Lambda ✓
- [x] Added `load_ml_model()` function
- [x] Loads model from S3: `s3://cloud-log-analyzer/ml_model/isolation_forest.pkl`
- [x] Implements model caching (load once, reuse)
- [x] Graceful fallback if model unavailable

### 4. Hybrid Scoring System ✓
- [x] Rule-based score (Sr) from alert count
- [x] ML score (Sa) from model decision function
- [x] Hybrid formula: Sh = 0.6 × Sr + 0.4 × Sa
- [x] Risk score conversion: risk = int((Sh + 1) × 50)
- [x] Risk levels: LOW/MEDIUM/HIGH/CRITICAL

### 5. DynamoDB Schema Updates ✓
- [x] ProcessedLogs: Added `ml_score` field
- [x] SecurityAlerts: Added 5 new fields
  - `anomaly_score` (Sa)
  - `rule_score` (Sr)
  - `hybrid_score` (Sh)
  - `final_score` (same as hybrid)
  - `risk_score` (0-100)
  - `risk_level` (text)

### 6. Testing & Documentation ✓
- [x] Created comprehensive test suite (`test_week6_ml_integration.py`)
- [x] Created `requirements-week6.txt`
- [x] Created `WEEK6_ML_INTEGRATION.md` guide
- [x] All 6 test categories included

---

## 📦 FILES CREATED

```
Cloud-log-analyzer/
├── train_ml_model.py           [NEW] ML training script
├── feature_extraction.py       [NEW] Feature utilities
├── test_week6_ml_integration.py [NEW] Comprehensive tests
├── requirements-week6.txt      [NEW] Python dependencies
├── WEEK6_ML_INTEGRATION.md     [NEW] Implementation guide
└── lambda/
    └── lambda_function.py      [UPDATED] ML integration
```

---

## 🚀 QUICK START

### 1. Install Dependencies
```bash
pip install -r requirements-week6.txt
```

### 2. Train ML Model
```bash
python train_ml_model.py
# Output: ml_model.pkl (50KB)
```

### 3. Upload Model to S3
```bash
aws s3 cp ml_model.pkl s3://cloud-log-analyzer/ml_model/isolation_forest.pkl
```

### 4. Test Locally
```bash
python test_week6_ml_integration.py
# Expected: ✅ ALL TESTS PASSED!
```

### 5. Deploy Lambda
Upload updated `lambda/lambda_function.py` to AWS Lambda

### 6. Verify in CloudWatch
Check Lambda logs for:
```
✅ ML model loaded successfully!
🤖 Extracting features and calculating ML scores...
🎯 Computing hybrid scores and risk levels...
```

---

## 📊 SCORING FORMULA REFERENCE

### Rules-Based Score (Sr)
```
0 alerts  → -1.0 (normal)
1 alert   → -0.5
2 alerts  →  0.0
3+ alerts →  0.5-1.0 (suspicious)
```

### ML Score (Sa)
```
From Isolation Forest decision_function
Range: [-1, 1]
Negative → Normal, Positive → Anomalous
```

### Hybrid Score (Sh)
```
Sh = 0.6 × Sr + 0.4 × Sa
Range: [-1, 1]
60% rule-based weight, 40% ML weight
```

### Risk Score (0-100)
```
risk = int((Sh + 1) × 50)
-1.0 → 0   (safest)
 0.0 → 50  (medium)
 1.0 → 100 (most critical)
```

### Risk Level
```
<30   → LOW      (green)
30-59 → MEDIUM   (yellow)
60-84 → HIGH     (orange)
≥85   → CRITICAL (red)
```

---

## 🔒 Security Considerations

1. **Model Storage**: Model is stored in S3 with restricted access
2. **Lambda IAM**: Ensure Lambda has S3:GetObject permission for model
3. **Model Loading**: Happens on first invocation only (cached after)
4. **Fallback**: If model unavailable, system uses rule-based only
5. **No Feature Leakage**: Features extracted locally in Lambda

---

## 📈 EXPECTED BEHAVIOR

### Lambda Invocation Flow
```
1. Validate S3 event
2. Load ML model from S3 (if not cached)
3. Parse logs from S3 file
4. Extract features for each user
5. Calculate ML scores (Sa) for each user
6. Run 7 rule-based detection rules
7. Calculate hybrid scores (Sh) for each alert
8. Convert to risk scores (0-100)
9. Determine risk levels
10. Store in DynamoDB with all scores
11. Return success response
```

### Example Output
```json
{
  "statusCode": 200,
  "body": {
    "total_logs": 150,
    "logs_stored": 150,
    "alerts_detected": 12,
    "invalid_logs": 0,
    "message": "WEEK 6: ML + Hybrid anomaly detection complete",
    "rules_executed": 7,
    "ml_model_loaded": true,
    "alpha": 0.6
  }
}
```

---

## 🧪 TEST COVERAGE

✓ Feature extraction test
✓ Rule-based scoring test
✓ Hybrid scoring test
✓ Risk score conversion test
✓ ML model training test
✓ End-to-end integration test

All tests in `test_week6_ml_integration.py`

---

## 📝 NOTES FOR LAKSHMAN (Week 7)

### Alert System Upgrades Needed
1. Modify Gmail alert format to include risk scores
2. Add risk level to alert subject/body
3. Include anomaly explanation in email
4. Send alerts only if risk_score > threshold

### Database Schema Already Updated
- All required fields added in Week 6
- Ready for Week 7 alert improvements

---

## ✨ WHAT'S NEXT (Week 7-10)

**Week 7:** Alert System Upgrade
- Enhanced Gmail alerts with risk scores
- Alert threshold configuration

**Week 8:** Database Schema Improvements
- DynamoDB optimization
- Indexing for risk-based queries

**Week 9:** Dashboard Visualization
- Risk level charts
- Anomaly trend visualization
- High-risk users display

**Week 10:** Final Validation
- End-to-end system testing
- Performance optimization
- Documentation completion

---

## 💡 KEY IMPROVEMENTS IN WEEK 6

### Before Week 6 (Rule-Based Only)
```
Alerts detected → Boolean (alert or no alert)
Risk assessment → Severity levels only
No quantification → Can't rank threats
```

### After Week 6 (Hybrid System)
```
Multiple anomaly signals → Combined via hybrid formula
Risk quantified → 0-100 scale
ML pattern detection → Catches subtle anomalies
Transparent scoring → Sr, Sa, Sh all visible
```

---

## 🎯 SUCCESS CRITERIA

- [x] Feature extraction implemented
- [x] ML model training working
- [x] Lambda loads model from S3
- [x] Hybrid scoring calculated
- [x] Risk scores stored in DynamoDB
- [x] All tests passing
- [x] Documentation complete
- [x] Ready for Lakshman's Week 7 tasks

---

**Status: ✅ WEEK 6 COMPLETE**

All tasks for Shravan's Week 6 (ML Integration) are implemented, tested, and documented!
