# 🔐 HYBRID LAMBDA - CROSS-ACCOUNT + WEEK 5 DETECTION

## ✅ What Changed?

Your Lambda now combines:
1. **Cross-Account Access** (from previous code)
2. **7 Advanced Detection Rules** (from WEEK 5)
3. **Batch Performance Optimization** (from WEEK 5)

---

## 📝 MODIFICATIONS MADE

### Only 1 Change - DynamoDB Initialization

**OLD (Direct DynamoDB):**
```python
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

**NEW (Cross-Account STS Assume Role):**
```python
# 🔐 Cross-Account Role ARN (Friends AWS Account)
CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::502881461360:role/DynamoDBCrossAccountRole"

def get_dynamodb():
    """🔐 Assume cross-account role and return DynamoDB resource"""
    try:
        sts_client = boto3.client('sts')
        assumed_role = sts_client.assume_role(
            RoleArn=CROSS_ACCOUNT_ROLE_ARN,
            RoleSessionName='cross-account-anomaly-detection'
        )
        
        credentials = assumed_role['Credentials']
        dynamodb = boto3.resource(
            'dynamodb',
            region_name='us-east-1',
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        return dynamodb
    except ClientError as e:
        print(f"❌ Error assuming cross-account role: {e}")
        raise

# Initialize DynamoDB via assumed role
dynamodb = get_dynamodb()
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

---

## 🎯 Everything Else UNCHANGED

✅ All 7 detection rules remain the same
✅ Batch writes for performance
✅ Validation and error handling
✅ Response formatting
✅ Complete lambda_handler logic

---

## 💡 KEY BENEFITS

```
Your Lambda                    Friend's AWS Account
    ↓                                  ↓
  Lambda ----[STS Assume Role]---→ DynamoDB
  (detect)                        (store)
    
- Your: Run detection rules
- Friend: Store data in their account
- Secure: No sharing of AWS credentials
```

---

## 🚀 FILES UPDATED

✅ `lambda/lambda_function.py` — With cross-account + WEEK 5 detection
✅ `LAMBDA_CODE_FOR_DEPLOYMENT.py` — Copy-paste ready with cross-account

---

## ⚠️ IMPORTANT: Update the Role ARN

Before deployment, verify/update:
```python
CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::502881461360:role/DynamoDBCrossAccountRole"
```

**Replace with:**
- Friend's AWS Account ID (in the ARN)
- Correct role name (DynamoDBCrossAccountRole)

Ask your friend to confirm:
1. Role name: `DynamoDBCrossAccountRole`
2. AWS Account ID: `502881461360` (or their correct ID)

---

## ✅ Ready to Deploy?

All modifications are backward compatible:
- Same 7 detection rules
- Same batch performance
- Just adds cross-account security
- No breaking changes

---

**Modified files are ready for AWS deployment!** 🚀
