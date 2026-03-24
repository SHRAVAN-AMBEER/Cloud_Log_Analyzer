#!/bin/bash

# AWS Infrastructure Setup Script for Cloud Log Analyzer Week 4
# This script creates all required AWS resources

set -e

# Configuration
AWS_REGION="us-east-1"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
BUCKET_NAME="cloud-log-analyzer-${ACCOUNT_ID}"
LAMBDA_ROLE_NAME="CloudLogAnalyzerLambdaRole"
LAMBDA_FUNCTION_NAME="log-analyzer-processor"

echo "🚀 Starting AWS Infrastructure Setup..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Region: $AWS_REGION"
echo "Account ID: $ACCOUNT_ID"
echo "Bucket: $BUCKET_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Step 1: Create DynamoDB Tables
echo ""
echo "📊 Step 1: Creating DynamoDB Tables..."

echo "  Creating SecurityAlerts table..."
aws dynamodb create-table \
    --table-name SecurityAlerts \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION 2>/dev/null || echo "  ⚠️  Table may already exist"

echo "  Creating ProcessedLogs table..."
aws dynamodb create-table \
    --table-name ProcessedLogs \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region $AWS_REGION 2>/dev/null || echo "  ⚠️  Table may already exist"

echo "✅ DynamoDB Tables created"

# Step 2: Wait for tables to be active
echo ""
echo "⏳ Waiting for tables to be active..."
aws dynamodb wait table-exists --table-name SecurityAlerts --region $AWS_REGION
aws dynamodb wait table-exists --table-name ProcessedLogs --region $AWS_REGION
echo "✅ All tables active"

# Step 3: Create IAM Role (if not exists)
echo ""
echo "🔐 Step 2: Setting up IAM Role..."

# Check if role exists
if aws iam get-role --role-name $LAMBDA_ROLE_NAME 2>/dev/null; then
    echo "  Role already exists"
else
    echo "  Creating new role..."
    
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

    aws iam create-role \
        --role-name $LAMBDA_ROLE_NAME \
        --assume-role-policy-document file://trust-policy.json
    
    rm trust-policy.json
fi

# Update policy
echo "  Updating IAM policy..."

cat > lambda-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3ReadAccess",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::${BUCKET_NAME}/*"
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
        "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/SecurityAlerts",
        "arn:aws:dynamodb:${AWS_REGION}:${ACCOUNT_ID}:table/ProcessedLogs"
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
      "Resource": "arn:aws:logs:${AWS_REGION}:${ACCOUNT_ID}:log-group:/aws/lambda/*"
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $LAMBDA_ROLE_NAME \
    --policy-name CloudLogAnalyzerDynamoDBPolicy \
    --policy-document file://lambda-policy.json

rm lambda-policy.json

ROLE_ARN=$(aws iam get-role --role-name $LAMBDA_ROLE_NAME --query 'Role.Arn' --output text)
echo "✅ IAM Role created: $ROLE_ARN"

# Step 4: Deploy Lambda Function
echo ""
echo "⚡ Step 3: Deploying Lambda Function..."

if [ -f "lambda/lambda_function.py" ]; then
    cd lambda
    
    # Package Lambda
    echo "  Packaging Lambda function..."
    zip -q lambda_function.zip lambda_function.py 2>/dev/null || true
    
    # Sleep for role to propagate
    echo "  Waiting for IAM role to propagate..."
    sleep 5
    
    # Check if function exists
    if aws lambda get-function --function-name $LAMBDA_FUNCTION_NAME --region $AWS_REGION 2>/dev/null; then
        echo "  Updating existing Lambda function..."
        aws lambda update-function-code \
            --function-name $LAMBDA_FUNCTION_NAME \
            --zip-file fileb://lambda_function.zip \
            --region $AWS_REGION > /dev/null
    else
        echo "  Creating new Lambda function..."
        aws lambda create-function \
            --function-name $LAMBDA_FUNCTION_NAME \
            --runtime python3.11 \
            --role $ROLE_ARN \
            --handler lambda_function.lambda_handler \
            --zip-file fileb://lambda_function.zip \
            --timeout 60 \
            --memory-size 256 \
            --region $AWS_REGION > /dev/null
    fi
    
    rm lambda_function.zip
    cd ..
    echo "✅ Lambda Function deployed"
else
    echo "❌ lambda/lambda_function.py not found!"
    exit 1
fi

# Step 5: Verify everything
echo ""
echo "✅ AWS Infrastructure Setup Complete!"
echo ""
echo "📋 Summary:"
echo "  ✅ DynamoDB Tables: SecurityAlerts, ProcessedLogs"
echo "  ✅ IAM Role: $LAMBDA_ROLE_NAME"
echo "  ✅ Lambda Function: $LAMBDA_FUNCTION_NAME"
echo ""
echo "🔧 Next Steps:"
echo "  1. Configure S3 event trigger for Lambda"
echo "  2. Test the Lambda function"
echo "  3. Upload test logs to S3"
echo ""
echo "📖 For more details, see: docs/AWS_INFRASTRUCTURE_SETUP.md"
