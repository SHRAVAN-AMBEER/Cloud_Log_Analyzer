# Instructions for Friend: Update Lambda for Cross-Account DynamoDB Access

## Overview

Your friend has set up DynamoDB tables in their AWS account. Your Lambda function is in your account. You need to update the Lambda code to write to their DynamoDB tables using cross-account access.

---

## 📋 Information You Need From Your Friend

Ask your friend to provide these 2 things:

1. **Their AWS Account ID** (12-digit number)
   - They can get it: AWS Console → Account → Account ID
   - Example: `123456789012`

2. **Cross-Account Role ARN**
   - They should have created: `DynamoDBCrossAccountRole`
   - ARN format: `arn:aws:iam::123456789012:role/DynamoDBCrossAccountRole`

**Save these values - you'll need them in Step 2**

---

## ✅ STEP-BY-STEP INSTRUCTIONS

### STEP 1: Get the Updated Lambda Code

The updated `lambda_function.py` is on GitHub in the `feature/lambda-processing` branch.

Pull the latest code:

```bash
cd /path/to/Cloud-log-analyzer
git pull origin feature/lambda-processing
```

Or copy the code from: `lambda/lambda_function.py`

---

### STEP 2: Update Lambda Code for Cross-Account Access

Open your Lambda function code and **replace the first 11 lines** with this:

**OLD CODE (lines 1-11):**
```python
import json
import boto3
from datetime import datetime

# AWS Clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# DynamoDB Tables (Week 4)
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

**NEW CODE (replace with this):**
```python
import json
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# AWS Clients
s3 = boto3.client('s3')

# Cross-Account DynamoDB Access
CROSS_ACCOUNT_ROLE_ARN = 'arn:aws:iam::FRIEND_ACCOUNT_ID:role/DynamoDBCrossAccountRole'

def get_cross_account_dynamodb():
    """Assume cross-account role and return DynamoDB resource"""
    try:
        sts_client = boto3.client('sts')
        assumed_role = sts_client.assume_role(
            RoleArn=CROSS_ACCOUNT_ROLE_ARN,
            RoleSessionName='cross-account-dynamodb-session'
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
        print(f"Error assuming cross-account role: {e}")
        raise

# Initialize DynamoDB (will be called when needed)
dynamodb = get_cross_account_dynamodb()
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

**IMPORTANT:** Replace `FRIEND_ACCOUNT_ID` with your friend's actual AWS Account ID (12-digit number).

Example:
```python
CROSS_ACCOUNT_ROLE_ARN = 'arn:aws:iam::123456789012:role/DynamoDBCrossAccountRole'
```

---

### STEP 3: Keep the Rest of the Code

The rest of the file stays **exactly the same**:
- `store_alert_in_dynamodb()` function - NO CHANGES
- `store_processed_log_in_dynamodb()` function - NO CHANGES
- `lambda_handler()` function - NO CHANGES

Only lines 1-11 are replaced!

---

### STEP 4: Update Lambda IAM Permissions

Your Lambda role needs permission to assume the cross-account role.

1. Go to **AWS Lambda Console**
2. Click your Lambda function: `log-analyzer-processor`
3. Scroll to **Execution role** section
4. Click the role name (opens IAM)
5. Click **Add permissions** → **Create inline policy**
6. Click **JSON** tab
7. Paste this:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::FRIEND_ACCOUNT_ID:role/DynamoDBCrossAccountRole"
    }
  ]
}
```

**Replace `FRIEND_ACCOUNT_ID`** with your friend's account ID.

8. Click **Review policy**
9. Name: `AssumeCrossAccountDynamoDBRole`
10. Click **Create policy**

---

### STEP 5: Deploy Updated Lambda

1. Go to **AWS Lambda Console**
2. Click your function
3. In the code editor, paste the updated code (from Step 2)
4. Click **Deploy** button (top right)

---

### STEP 6: Test It Works

#### Test 1: Check Lambda Logs
```bash
aws logs tail /aws/lambda/log-analyzer-processor --follow
```

Look for any errors about assuming the role.

#### Test 2: Upload Test File to S3
```bash
aws s3 cp test_log.jsonl s3://YOUR_BUCKET/raw-logs/auth/2026/03/25/test.jsonl
```

#### Test 3: Check Your Friend's DynamoDB

Your friend should check:
```bash
aws dynamodb scan --table-name SecurityAlerts --region us-east-1
aws dynamodb scan --table-name ProcessedLogs --region us-east-1
```

Data should appear!

---

## ❌ Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"
- **Fix:** Make sure you added the IAM policy in Step 4
- **Fix:** Verify role ARN is correct
- **Fix:** Wait 1-2 minutes for IAM changes to propagate

### Error: "Role not found"
- **Fix:** Check the role ARN is exactly correct
- **Fix:** Verify your friend created the role `DynamoDBCrossAccountRole`

### Error: "AccessDenied" on DynamoDB
- **Fix:** Your friend needs to verify the cross-account role has DynamoDB permissions
- **Fix:** Check table names are exactly: `SecurityAlerts` and `ProcessedLogs`

### Lambda doesn't trigger from S3
- **Fix:** Verify S3 event notification is configured
- **Fix:** Check Lambda has S3 invoke permission
- **Fix:** Look at CloudWatch logs

---

## 📋 Quick Checklist

- [ ] Got friend's AWS Account ID
- [ ] Got cross-account role ARN
- [ ] Pulled updated code from GitHub
- [ ] Replaced lines 1-11 in Lambda
- [ ] Replaced `FRIEND_ACCOUNT_ID` in the code (TWO places)
- [ ] Added IAM permission for sts:AssumeRole
- [ ] Deployed Lambda function
- [ ] Tested with sample log file
- [ ] Verified data in DynamoDB

---

## 📝 Summary - What Changed

### Before:
```python
dynamodb = boto3.resource('dynamodb')
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

### After:
```python
# Now assumes friend's role to access their DynamoDB
dynamodb = get_cross_account_dynamodb()
ALERTS_TABLE = dynamodb.Table('SecurityAlerts')
PROCESSED_LOGS_TABLE = dynamodb.Table('ProcessedLogs')
```

**Rest of the code stays the same!**

---

## 🎯 Expected Result

When you upload logs to S3:
1. Lambda triggers
2. Lambda assumes your friend's role
3. Lambda reads from S3 (same account)
4. Lambda writes to friend's DynamoDB (cross-account)
5. Data appears in friend's SecurityAlerts and ProcessedLogs tables ✅

---

## 📞 Need Help?

If something doesn't work:
1. Check CloudWatch logs: `aws logs tail /aws/lambda/log-analyzer-processor`
2. Verify role ARN is exactly correct
3. Make sure IAM policy was added
4. Wait 2-3 minutes for IAM to propagate

---

**That's it! Your Lambda is now connected to your friend's DynamoDB! 🎉**
