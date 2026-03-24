# Week 4: AWS Infrastructure Setup - Quick Start Guide

## 📋 Current Progress

✅ **Completed:**
- Lambda function with DynamoDB integration
- DynamoDB table schema design
- AWS setup documentation

⏳ **Current Step:** Set up AWS resources

---

## 🚀 Quick Setup (5 minutes)

### Prerequisites
1. AWS Account
2. AWS CLI installed and configured
3. Python 3.9+ (already configured in your project)

### Option 1: Automated Setup (Recommended)

**For Windows (PowerShell):**
```powershell
.\setup-aws-infrastructure.ps1
```

**For Mac/Linux (Bash):**
```bash
chmod +x setup-aws-infrastructure.sh
./setup-aws-infrastructure.sh
```

This script will automatically:
- ✅ Create DynamoDB tables (SecurityAlerts, ProcessedLogs)
- ✅ Create IAM role with proper permissions
- ✅ Deploy Lambda function to AWS
- ✅ Configure all necessary access policies

---

### Option 2: Manual AWS Console Setup

#### Step 1: Create DynamoDB Tables

**Table 1: SecurityAlerts**
1. Go to AWS DynamoDB Console
2. Click "Create table"
3. Settings:
   - Name: `SecurityAlerts`
   - Partition key: `user_id` (String)
   - Sort key: `timestamp` (String)
   - Billing: On-demand
4. Create

**Table 2: ProcessedLogs**
- Same as above but name: `ProcessedLogs`

#### Step 2: Create IAM Role

1. Go to AWS IAM → Roles
2. Create new role
3. Name: `CloudLogAnalyzerLambdaRole`
4. Trust: Lambda service
5. Add inline policy (use JSON below):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["dynamodb:PutItem", "dynamodb:Query"],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/SecurityAlerts",
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/ProcessedLogs"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/lambda/*"
    }
  ]
}
```

#### Step 3: Deploy Lambda

1. Go to AWS Lambda → Create function
2. Settings:
   - Name: `log-analyzer-processor`
   - Runtime: Python 3.11
   - Role: Select `CloudLogAnalyzerLambdaRole`
3. Upload code from `lambda/lambda_function.py`
4. Deploy

---

## 🧪 Local Testing (Before AWS Deployment)

Run the local test to verify everything is working:

```bash
python test_lambda_local.py
```

Expected output:
```
✅ Lambda Function Local Test
✅ All structural tests passed!
✅ Function imports correctly
✅ Handler accepts event and context
```

---

## 🔗 Configure S3 Trigger

Once Lambda is deployed, configure S3 to trigger it:

```bash
aws s3api put-bucket-notification-configuration \
    --bucket YOUR_BUCKET_NAME \
    --notification-configuration '{
    "LambdaFunctionConfigurations": [
        {
            "LambdaFunctionArn": "arn:aws:lambda:us-east-1:ACCOUNT_ID:function:log-analyzer-processor",
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {"Name": "prefix", "Value": "raw-logs/auth/"},
                        {"Name": "suffix", "Value": ".jsonl"}
                    ]
                }
            }
        }
    ]
}'
```

Also grant Lambda permission:

```bash
aws lambda add-permission \
    --function-name log-analyzer-processor \
    --statement-id AllowS3Invoke \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::YOUR_BUCKET_NAME
```

---

## ✅ Verify Setup

### 1. Check DynamoDB Tables
```bash
aws dynamodb list-tables
```
Should show: `SecurityAlerts`, `ProcessedLogs`

### 2. Check Lambda Function
```bash
aws lambda get-function --function-name log-analyzer-processor
```
Should show function details

### 3. Check IAM Role
```bash
aws iam get-role --role-name CloudLogAnalyzerLambdaRole
```
Should show role ARN

---

## 🧪 End-to-End Test

1. **Upload test logs to S3:**
   ```bash
   aws s3 cp backend/logs/auth_logs.jsonl s3://YOUR_BUCKET/raw-logs/auth/2026/03/24/test.jsonl
   ```

2. **Check Lambda execution:**
   ```bash
   aws logs tail /aws/lambda/log-analyzer-processor --follow
   ```

3. **Query DynamoDB for results:**
   ```bash
   aws dynamodb scan --table-name SecurityAlerts
   ```

---

## 📊 Expected DynamoDB Entries

After running end-to-end test, you should see:

**SecurityAlerts Table:**
```json
{
  "user_id": "admin",
  "timestamp": "2026-03-24T10:30:45Z",
  "ip": "192.168.1.100",
  "threat_flag": true,
  "failed_attempts": 3,
  "alert_type": "MULTIPLE_FAILED_LOGINS",
  "severity": "MEDIUM"
}
```

**ProcessedLogs Table:**
- All authentication logs from the uploaded file
- Each with `threat_flag: false/true`

---

## 🔧 Troubleshooting

### Error: "NoCredentialsError"
- Run `aws configure`
- Enter AWS Access Key ID and Secret Access Key

### Error: "Table not found"
- Ensure tables are created in correct region (us-east-1)
- Check table names match exactly (case-sensitive)

### Error: "AccessDenied" on DynamoDB
- Check IAM role has DynamoDB permissions
- Verify policy includes correct table ARNs

### Lambda not triggered by S3
- Verify S3 notification configuration
- Check Lambda has S3 invoke permission
- Look at Lambda CloudWatch logs for errors

---

## 📈 What's Next?

After successful AWS setup:

1. ✅ Verify all resources created
2. ✅ Test end-to-end pipeline
3. ⏳ Build Admin Dashboard (Phase 2)
4. ⏳ Add ML Anomaly Detection (Phase 3)
5. ⏳ Implement Alert System (Phase 4)

---

## 📚 Resources

- [AWS_INFRASTRUCTURE_SETUP.md](AWS_INFRASTRUCTURE_SETUP.md) - Detailed setup guide
- [WEEK4_DYNAMODB_INTEGRATION.md](WEEK4_DYNAMODB_INTEGRATION.md) - DynamoDB details
- AWS CLI Reference: https://docs.aws.amazon.com/cli/
- DynamoDB Docs: https://docs.aws.amazon.com/dynamodb/

---

## 💡 Tips

- Use `PAY_PER_REQUEST` billing for testing (no minimum charges)
- Enable CloudWatch logs to monitor Lambda execution
- Use AWS Secrets Manager for sensitive credentials
- Test locally first before AWS deployment

---

**You are on track for Week 4! Good luck! 🎉**
