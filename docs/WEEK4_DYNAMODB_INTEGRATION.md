# Week 4: DynamoDB Integration

## Objective
Store processed logs and detected security alerts in DynamoDB for persistent storage and dashboard visualization.

---

## Implementation Summary

### Tables Created

#### 1. **SecurityAlerts Table**
Stores detected security anomalies and threats.

| Attribute | Type | Key | Purpose |
|-----------|------|-----|---------|
| `user_id` | String | **Partition Key** | Username that triggered alert |
| `timestamp` | String | **Sort Key** | ISO-8601 timestamp of detection |
| `ip` | String | - | Source IP address |
| `threat_flag` | Boolean | - | Whether this is a confirmed threat |
| `failed_attempts` | Number | - | Number of failed login attempts |
| `alert_type` | String | - | Type of alert (e.g., "MULTIPLE_FAILED_LOGINS") |
| `severity` | String | - | "LOW", "MEDIUM", "HIGH", "CRITICAL" |
| `status` | String | - | "ACTIVE", "RESOLVED", "FALSE_POSITIVE" |

#### 2. **ProcessedLogs Table**
Stores all authentication logs for audit and analysis.

| Attribute | Type | Key | Purpose |
|-----------|------|-----|---------|
| `user_id` | String | **Partition Key** | Username attempting login |
| `timestamp` | String | **Sort Key** | ISO-8601 timestamp of attempt |
| `ip` | String | - | Source IP address |
| `threat_flag` | Boolean | - | Whether part of a threat |
| `user_agent` | String | - | Browser/client info |
| `login_status` | String | - | "success" or "failure" |
| `processed_at` | String | - | When Lambda processed this |

---

## Lambda Function Updates (Week 4)

### New Functions Added

```python
def store_alert_in_dynamodb(username, ip, failed_attempts, timestamp, threat_flag=True)
```
- Stores detected anomalies in SecurityAlerts table
- Sets severity based on failed attempts
- Status set to "ACTIVE" by default

```python
def store_processed_log_in_dynamodb(log_entry, is_threat=False)
```
- Stores all processed logs in ProcessedLogs table
- Marks if log is part of a threat pattern
- Timestamps when Lambda processed the log

### Enhanced lambda_handler()
- Now processes all logs and stores in DynamoDB
- Detects multiple failed logins (≥3 attempts)
- Creates alert records with severity levels
- Returns detailed response with counts

---

## AWS Setup Required

### 1. Create DynamoDB Tables

**Option A: AWS Console**
1. Go to DynamoDB → Create table
2. Table name: `SecurityAlerts`
3. Partition key: `user_id` (String)
4. Sort key: `timestamp` (String)
5. Billing: On-demand
6. Repeat for `ProcessedLogs` table

**Option B: CloudFormation**

```yaml
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
```

### 2. Update Lambda IAM Policy

Add DynamoDB permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/SecurityAlerts",
        "arn:aws:dynamodb:us-east-1:ACCOUNT_ID:table/ProcessedLogs"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::YOUR_BUCKET_NAME/*"
    }
  ]
}
```

### 3. Update Lambda Environment

- Lambda already has boto3 for DynamoDB access
- No additional dependencies needed
- Tables must be in same AWS region as Lambda

---

## Query Examples

### Get all alerts for a user
```python
response = ALERTS_TABLE.query(
    KeyConditionExpression='user_id = :user',
    ExpressionAttributeValues={':user': 'admin'}
)
```

### Get high-severity alerts
```python
response = ALERTS_TABLE.scan(
    FilterExpression='severity = :sev AND #status = :status',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={
        ':sev': 'HIGH',
        ':status': 'ACTIVE'
    }
)
```

### Get all logs for a specific user
```python
response = PROCESSED_LOGS_TABLE.query(
    KeyConditionExpression='user_id = :user',
    ExpressionAttributeValues={':user': 'admin'}
)
```

---

## Testing

1. Ensure tables are created in AWS
2. Deploy updated Lambda function
3. Upload sample log file to S3
4. Lambda should trigger and populate both tables
5. Query tables to verify data

---

## Cost Estimate (On-Demand)

- Write Units: $1.25 per million
- Read Units: $0.25 per million
- Typical: ~$0.50-2.00/month for small deployments

---

## Next Steps (Week 5+)

- [ ] Build admin dashboard to query DynamoDB
- [ ] Add ML anomaly detection (Isolation Forest)
- [ ] Implement email alerts
- [ ] Create CloudWatch dashboards
- [ ] Add table TTL for log rotation
