import json
import boto3
from dotenv import load_dotenv

load_dotenv()

# Cross-account role ARN
CROSS_ACCOUNT_ROLE_ARN = "arn:aws:iam::502881461360:role/DynamoDBCrossAccountRole"

def get_assumed_credentials():
    try:
        sts_client = boto3.client('sts', region_name='us-east-1')
        assumed = sts_client.assume_role(
            RoleArn=CROSS_ACCOUNT_ROLE_ARN,
            RoleSessionName="TestingSession"
        )
        return assumed['Credentials']
    except Exception as e:
        print(f"STS AssumeRole Failed: {e}")
        return None

creds = get_assumed_credentials()

if creds:
    lambda_client = boto3.client(
        'lambda', region_name='us-east-1',
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )
    dynamodb = boto3.resource(
        'dynamodb', region_name='us-east-1',
        aws_access_key_id=creds['AccessKeyId'],
        aws_secret_access_key=creds['SecretAccessKey'],
        aws_session_token=creds['SessionToken']
    )
else:
    # Fallback to local default profile (which will likely fail if restricted)
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

def compute_risk(feature, ml_score):
    login_hour, failed_attempts, ip_count, failure_ratio = feature
    Sr = 0.0
    if failed_attempts > 3:    Sr += 0.4
    if failure_ratio > 0.5:    Sr += 0.3
    if ip_count > 3:           Sr += 0.3
    Sr = min(1.0, Sr)
    Sa = 0.5 - ml_score
    Sa = max(0.0, min(1.0, Sa))
    alpha = 0.6
    Sh = alpha * Sr + (1 - alpha) * Sa
    risk_score = int(Sh * 100)
    if risk_score < 25:
        level = "LOW"
    elif risk_score < 55:
        level = "MEDIUM"
    elif risk_score < 80:
        level = "HIGH"
    else:
        level = "CRITICAL"
    return risk_score, level

def run_test_1():
    print("--- TEST 1: ML Lambda Input/Output Validation ---")
    normal_payload = {"features": [[14, 0, 1, 0.0]]}
    anomaly_payload = {"features": [[3, 15, 8, 0.95]]}
    
    pass_normal = False
    pass_anomaly = False

    try:
        res1 = lambda_client.invoke(FunctionName='ml-lambda-function', InvocationType='RequestResponse', Payload=json.dumps(normal_payload))
        out1 = json.loads(res1['Payload'].read())
        body1 = json.loads(out1['body'])
        ml_score1 = body1['scores'][0]
        r1, l1 = compute_risk(normal_payload['features'][0], ml_score1)
        print(f"Normal Payload -> raw_score: {ml_score1}, risk_score: {r1}, expected_level: {l1}")
        if l1 in ["LOW", "MEDIUM"]: pass_normal = True
    except Exception as e:
        print(f"Normal Payload Failed: {e}")

    try:
        res2 = lambda_client.invoke(FunctionName='ml-lambda-function', InvocationType='RequestResponse', Payload=json.dumps(anomaly_payload))
        out2 = json.loads(res2['Payload'].read())
        body2 = json.loads(out2['body'])
        ml_score2 = body2['scores'][0]
        r2, l2 = compute_risk(anomaly_payload['features'][0], ml_score2)
        print(f"Anomaly Payload -> raw_score: {ml_score2}, risk_score: {r2}, expected_level: {l2}")
        if l2 in ["HIGH", "CRITICAL"]: pass_anomaly = True
    except Exception as e:
        print(f"Anomaly Payload Failed: {e}")

    result = pass_normal and pass_anomaly
    print(f"Result: {'PASS' if result else 'FAIL'}\n")
    return result

def run_test_2():
    print("--- TEST 2: DynamoDB Write Validation (company_id present) ---")
    try:
        table = dynamodb.Table('SecurityAlerts')
        response = table.scan(Limit=50) # scan a few records
        found = False
        for item in response.get('Items', []):
            cid = item.get('company_id')
            if cid and cid != 'UNKNOWN':
                found = True
                print(f"✅ company_id found: {cid}")
                break
        if not found:
            print("❌ company_id missing from all records")
        print(f"Result: {'PASS' if found else 'FAIL'}\n")
        return found
    except Exception as e:
        print(f"Test 2 failed with exception: {e}")
        return False

def run_test_3():
    print("--- TEST 3: ProcessedLogs Primary Key Validation ---")
    try:
        table = dynamodb.Table('ProcessedLogs')
        response = table.scan(Limit=50)
        found = False
        if response.get('Items'):
            for item in response.get('Items'):
                if 'log_id' in item:
                    found = True
                    print("✅ log_id present")
                    break
            if not found:
                print("❌ log_id missing — batch writes were silently failing")
        else:
            print("❌ No items found in ProcessedLogs")
        print(f"Result: {'PASS' if found else 'FAIL'}\n")
        return found
    except Exception as e:
        print(f"Test 3 failed with exception: {e}")
        return False

def run_test_4():
    print("--- TEST 4: Risk Score Sanity Check ---")
    tests = [
        ([3, 10, 5, 0.9], -0.3, ["HIGH", "CRITICAL"]),
        ([14, 0, 1, 0.0], 0.1, ["LOW"]),
        ([22, 4, 2, 0.6], -0.1, ["MEDIUM", "HIGH"])
    ]
    all_pass = True
    for feat, ml_score, expected_levels in tests:
        r, l = compute_risk(feat, ml_score)
        passed = l in expected_levels
        print(f"Input {feat}, ML={ml_score} -> Score: {r}, Level: {l} | Expected: {expected_levels} | {'PASS' if passed else 'FAIL'}")
        if not passed: all_pass = False
    
    print(f"Result: {'PASS' if all_pass else 'FAIL'}\n")
    return all_pass

if __name__ == "__main__":
    t1 = run_test_1()
    t2 = run_test_2()
    t3 = run_test_3()
    t4 = run_test_4()
    
    print("=== TEST RESULTS ===")
    print(f"Test 1 (ML Lambda): {'PASS' if t1 else 'FAIL'}")
    print(f"Test 2 (company_id): {'PASS' if t2 else 'FAIL'}")
    print(f"Test 3 (log_id): {'PASS' if t3 else 'FAIL'}")
    print(f"Test 4 (risk scoring): {'PASS' if t4 else 'FAIL'}")
