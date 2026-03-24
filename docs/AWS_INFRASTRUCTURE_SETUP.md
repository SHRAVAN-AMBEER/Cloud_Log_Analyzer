# AWS Infrastructure Setup - Week 4

## Overview
This guide will help you set up all required AWS resources for the Cloud Log Analyzer project.

---

## Prerequisites
- AWS Account with permissions to create DynamoDB, Lambda, S3, and IAM resources
- AWS CLI installed and configured locally
- Appropriate AWS credentials

---

## Step 1: Create DynamoDB Tables

### Option A: Using AWS Management Console

1. **Create SecurityAlerts Table:**
   - Go to AWS DynamoDB Console
   - Click "Create table"
   - Table name: `SecurityAlerts`
   - Partition key: `user_id` (String)
   - Sort key: `timestamp` (String)
   - Billing mode: On-demand
   - Click "Create"

2. **Create ProcessedLogs Table:**
   - Click "Create table"
   - Table name: `ProcessedLogs`
   - Partition key: `user_id` (String)
   - Sort key: `timestamp` (String)
   - Billing mode: On-demand
   - Click "Create"

### Option B: Using AWS CLI

```bash
# Create SecurityAlerts table
aws dynamodb create-table \
    --table-name SecurityAlerts \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1

# Create ProcessedLogs table
aws dynamodb create-table \
    --table-name ProcessedLogs \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

### Option C: Using CloudFormation

Save this as `dynamodb-tables.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'DynamoDB Tables for Cloud Log Analyzer'

Resources:
  SecurityAlertsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: SecurityAlerts
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: timestamp
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH
        - AttributeName: timestamp
          KeyType: RANGE
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: false
      Tags:
        - Key: Project
          Value: CloudLogAnalyzer
        - Key: Week
          Value: '4'

  ProcessedLogsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: ProcessedLogs
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: timestamp
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH
        - AttributeName: timestamp
          KeyType: RANGE
      Tags:
        - Key: Project
          Value: CloudLogAnalyzer
        - Key: Week
          Value: '4'

Outputs:
  SecurityAlertsTableName:
    Description: Name of SecurityAlerts table
    Value: !Ref SecurityAlertsTable

  ProcessedLogsTableName:
    Description: Name of ProcessedLogs table
    Value: !Ref ProcessedLogsTable
```

Deploy with CloudFormation:

```bash
aws cloudformation create-stack \
    --stack-name cloud-log-analyzer-week4 \
    --template-body file://dynamodb-tables.yaml \
    --region us-east-1
```

---

## Step 2: Create/Update Lambda Execution Role

### Create IAM Policy Document

Save this as `lambda-dynamodb-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadAccess",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    },
    {
      "Sid": "DynamoDBWriteAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/SecurityAlerts",
        "arn:aws:dynamodb:us-east-1:YOUR_ACCOUNT_ID:table/ProcessedLogs"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-east-1:YOUR_ACCOUNT_ID:log-group:/aws/lambda/*"
    }
  ]
}
```

**Replace:**
- `YOUR_BUCKET_NAME` - Your S3 bucket name
- `YOUR_ACCOUNT_ID` - Your AWS Account ID (e.g., 123456789012)

### Create IAM Role (if not existing)

```bash
# Create trust policy document
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
    --role-name CloudLogAnalyzerLambdaRole \
    --assume-role-policy-document file://trust-policy.json

# Attach the policy
aws iam put-role-policy \
    --role-name CloudLogAnalyzerLambdaRole \
    --policy-name CloudLogAnalyzerDynamoDBPolicy \
    --policy-document file://lambda-dynamodb-policy.json
```

Get the Role ARN:

```bash
aws iam get-role --role-name CloudLogAnalyzerLambdaRole --query 'Role.Arn' --output text
```

---

## Step 3: Deploy Lambda Function

### Update Lambda Code

Your Lambda function is already updated in `lambda/lambda_function.py` with DynamoDB integration.

### Deploy to AWS

```bash
# Package the Lambda function
cd lambda
zip lambda_function.zip lambda_function.py

# Upload to Lambda
aws lambda update-function-code \
    --function-name log-analyzer-processor \
    --zip-file fileb://lambda_function.zip \
    --region us-east-1

# If function doesn't exist, create it:
aws lambda create-function \
    --function-name log-analyzer-processor \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/CloudLogAnalyzerLambdaRole \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://lambda_function.zip \
    --timeout 60 \
    --memory-size 256 \
    --region us-east-1
```

---

## Step 4: Create S3 Event Trigger

```bash
# Add S3 event notification to trigger Lambda
aws s3api put-bucket-notification-configuration \
    --bucket YOUR_BUCKET_NAME \
    --notification-configuration '{
    "LambdaFunctionConfigurations": [
        {
            "LambdaFunctionArn": "arn:aws:lambda:us-east-1:YOUR_ACCOUNT_ID:function:log-analyzer-processor",
            "Events": ["s3:ObjectCreated:*"],
            "Filter": {
                "Key": {
                    "FilterRules": [
                        {
                            "Name": "prefix",
                            "Value": "raw-logs/auth/"
                        },
                        {
                            "Name": "suffix",
                            "Value": ".jsonl"
                        }
                    ]
                }
            }
        }
    ]
}'
```

Also, add S3 invoke permission for Lambda:

```bash
aws lambda add-permission \
    --function-name log-analyzer-processor \
    --statement-id AllowS3Invoke \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::YOUR_BUCKET_NAME \
    --region us-east-1
```

---

## Step 5: Test the Setup

### Test 1: Verify DynamoDB Tables Exist

```bash
aws dynamodb list-tables --region us-east-1
```

Should show:
```
{
    "TableNames": [
        "ProcessedLogs",
        "SecurityAlerts"
    ]
}
```

### Test 2: Local Lambda Test (Before Deployment)

Create a test file `test_lambda.py`:

```python
import json
import sys
sys.path.insert(0, 'lambda')

from lambda_function import lambda_handler

# Mock S3 event
event = {
    "Records": [
        {
            "s3": {
                "bucket": {
                    "name": "YOUR_BUCKET_NAME"
                },
                "object": {
                    "key": "raw-logs/auth/2026/03/24/auth_logs_20260324T100000Z.jsonl"
                }
            }
        }
    ]
}

# Test the handler
try:
    response = lambda_handler(event, None)
    print("✅ Lambda test successful!")
    print(json.dumps(response, indent=2))
except Exception as e:
    print(f"❌ Lambda test failed: {e}")
    import traceback
    traceback.print_exc()
```

Run with:

```bash
python test_lambda.py
```

### Test 3: Query DynamoDB After Test

```bash
# Query SecurityAlerts
aws dynamodb scan \
    --table-name SecurityAlerts \
    --region us-east-1

# Query ProcessedLogs
aws dynamodb scan \
    --table-name ProcessedLogs \
    --region us-east-1
```

### Test 4: Check CloudWatch Logs

```bash
aws logs tail /aws/lambda/log-analyzer-processor --follow --region us-east-1
```

---

## Step 6: Verify Integration

1. ✅ DynamoDB tables created and accessible
2. ✅ Lambda role has correct permissions
3. ✅ Lambda function code deployed
4. ✅ S3 event trigger configured
5. ✅ Local test passes
6. ✅ CloudWatch logs show execution

---

## Troubleshooting

### Lambda cannot write to DynamoDB
- **Check:** IAM policy attached to Lambda role includes DynamoDB:PutItem
- **Fix:** Update role policy with correct table ARNs

### S3 event not triggering Lambda
- **Check:** S3 bucket notification configured correctly
- **Check:** Lambda has permission to be invoked by S3
- **Fix:** Verify bucket name and Lambda ARN are correct

### "Table not found" error
- **Check:** Table name matches exactly (case-sensitive)
- **Check:** Table is in same region as Lambda
- **Fix:** Verify table exists with `aws dynamodb list-tables`

### Permission denied when testing
- **Check:** AWS credentials are configured
- **Fix:** Run `aws configure` and enter credentials

---

## Next Steps

After successful setup:
1. Upload a test log file to S3
2. Verify Lambda executes
3. Query DynamoDB to confirm data storage
4. Move to Phase 2: Build Admin Dashboard

---

## Cost Estimation (Monthly)

| Service | Estimate |
|---------|----------|
| DynamoDB (On-demand) | $0.50 - $2.00 |
| Lambda Invocations | Free (within limits) |
| S3 Storage | $0.023 per GB |
| **Total** | **~$1-3/month** |

