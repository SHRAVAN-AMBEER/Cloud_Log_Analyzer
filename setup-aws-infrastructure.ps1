# AWS Infrastructure Setup Script for Cloud Log Analyzer Week 4 - PowerShell
# This script creates all required AWS resources

param(
    [string]$AwsRegion = "us-east-1",
    [string]$BucketName = $null
)

$ErrorActionPreference = "Stop"

# Get Account ID
$AccountId = aws sts get-caller-identity --query Account --output text
if (-not $BucketName) {
    $BucketName = "cloud-log-analyzer-$AccountId"
}

$LambdaRoleName = "CloudLogAnalyzerLambdaRole"
$LambdaFunctionName = "log-analyzer-processor"

Write-Host "🚀 Starting AWS Infrastructure Setup..." -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "Region: $AwsRegion" -ForegroundColor White
Write-Host "Account ID: $AccountId" -ForegroundColor White
Write-Host "Bucket: $BucketName" -ForegroundColor White
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan

# Step 1: Create DynamoDB Tables
Write-Host "`n📊 Step 1: Creating DynamoDB Tables..." -ForegroundColor Yellow

Write-Host "  Creating SecurityAlerts table..." -ForegroundColor Gray
$null = aws dynamodb create-table `
    --table-name SecurityAlerts `
    --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=timestamp,AttributeType=S `
    --key-schema AttributeName=user_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE `
    --billing-mode PAY_PER_REQUEST `
    --region $AwsRegion 2>$null

Write-Host "  Creating ProcessedLogs table..." -ForegroundColor Gray
$null = aws dynamodb create-table `
    --table-name ProcessedLogs `
    --attribute-definitions AttributeName=user_id,AttributeType=S AttributeName=timestamp,AttributeType=S `
    --key-schema AttributeName=user_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE `
    --billing-mode PAY_PER_REQUEST `
    --region $AwsRegion 2>$null

Write-Host "✅ DynamoDB Tables created" -ForegroundColor Green

# Step 2: Wait for tables to be active
Write-Host "`n⏳ Waiting for tables to be active..." -ForegroundColor Yellow
Write-Host "  (This may take a minute...)" -ForegroundColor Gray

$null = aws dynamodb wait table-exists --table-name SecurityAlerts --region $AwsRegion
$null = aws dynamodb wait table-exists --table-name ProcessedLogs --region $AwsRegion
Write-Host "✅ All tables active" -ForegroundColor Green

# Step 3: Create IAM Role
Write-Host "`n🔐 Step 2: Setting up IAM Role..." -ForegroundColor Yellow

try {
    $null = aws iam get-role --role-name $LambdaRoleName 2>$null
    Write-Host "  Role already exists" -ForegroundColor Gray
} catch {
    Write-Host "  Creating new role..." -ForegroundColor Gray
    
    $TrustPolicy = @{
        Version = "2012-10-17"
        Statement = @(
            @{
                Effect = "Allow"
                Principal = @{ Service = "lambda.amazonaws.com" }
                Action = "sts:AssumeRole"
            }
        )
    } | ConvertTo-Json

    $TrustPolicy | Out-File "trust-policy.json"
    
    $null = aws iam create-role `
        --role-name $LambdaRoleName `
        --assume-role-policy-document file://trust-policy.json
    
    Remove-Item "trust-policy.json" -Force
}

# Update policy
Write-Host "  Updating IAM policy..." -ForegroundColor Gray

$LambdaPolicy = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Sid = "S3ReadAccess"
            Effect = "Allow"
            Action = @("s3:GetObject")
            Resource = "arn:aws:s3:::$BucketName/*"
        },
        @{
            Sid = "DynamoDBWriteAccess"
            Effect = "Allow"
            Action = @("dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query")
            Resource = @(
                "arn:aws:dynamodb:$($AwsRegion):$($AccountId):table/SecurityAlerts",
                "arn:aws:dynamodb:$($AwsRegion):$($AccountId):table/ProcessedLogs"
            )
        },
        @{
            Sid = "CloudWatchLogs"
            Effect = "Allow"
            Action = @("logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents")
            Resource = "arn:aws:logs:$($AwsRegion):$($AccountId):log-group:/aws/lambda/*"
        }
    )
} | ConvertTo-Json

$LambdaPolicy | Out-File "lambda-policy.json"

$null = aws iam put-role-policy `
    --role-name $LambdaRoleName `
    --policy-name CloudLogAnalyzerDynamoDBPolicy `
    --policy-document file://lambda-policy.json

Remove-Item "lambda-policy.json" -Force

$RoleArn = aws iam get-role --role-name $LambdaRoleName --query 'Role.Arn' --output text
Write-Host "✅ IAM Role created: $RoleArn" -ForegroundColor Green

# Step 4: Deploy Lambda Function
Write-Host "`n⚡ Step 3: Deploying Lambda Function..." -ForegroundColor Yellow

if (Test-Path "lambda\lambda_function.py") {
    Push-Location lambda
    
    # Package Lambda
    Write-Host "  Packaging Lambda function..." -ForegroundColor Gray
    $null = Compress-Archive -Path "lambda_function.py" -DestinationPath "lambda_function.zip" -Force
    
    # Wait for role to propagate
    Write-Host "  Waiting for IAM role to propagate..." -ForegroundColor Gray
    Start-Sleep -Seconds 5
    
    # Check if function exists
    $FunctionExists = $null -ne (aws lambda get-function --function-name $LambdaFunctionName --region $AwsRegion 2>$null)
    
    if ($FunctionExists) {
        Write-Host "  Updating existing Lambda function..." -ForegroundColor Gray
        $null = aws lambda update-function-code `
            --function-name $LambdaFunctionName `
            --zip-file fileb://lambda_function.zip `
            --region $AwsRegion
    } else {
        Write-Host "  Creating new Lambda function..." -ForegroundColor Gray
        $null = aws lambda create-function `
            --function-name $LambdaFunctionName `
            --runtime python3.11 `
            --role $RoleArn `
            --handler lambda_function.lambda_handler `
            --zip-file fileb://lambda_function.zip `
            --timeout 60 `
            --memory-size 256 `
            --region $AwsRegion
    }
    
    Remove-Item "lambda_function.zip" -Force
    Pop-Location
    Write-Host "✅ Lambda Function deployed" -ForegroundColor Green
} else {
    Write-Host "❌ lambda/lambda_function.py not found!" -ForegroundColor Red
    exit 1
}

# Step 5: Verify tables
Write-Host "`n✅ AWS Infrastructure Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 Summary:" -ForegroundColor Cyan
Write-Host "  ✅ DynamoDB Tables: SecurityAlerts, ProcessedLogs" -ForegroundColor White
Write-Host "  ✅ IAM Role: $LambdaRoleName" -ForegroundColor White
Write-Host "  ✅ Lambda Function: $LambdaFunctionName" -ForegroundColor White
Write-Host ""
Write-Host "🔧 Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Configure S3 event trigger for Lambda" -ForegroundColor White
Write-Host "  2. Test the Lambda function" -ForegroundColor White
Write-Host "  3. Upload test logs to S3" -ForegroundColor White
Write-Host ""
Write-Host "📖 For more details, see: docs/AWS_INFRASTRUCTURE_SETUP.md" -ForegroundColor Cyan
Write-Host ""
