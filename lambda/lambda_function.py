import json
import boto3

s3 = boto3.client('s3')

def lambda_handler(event, context):
    print("🚀 Lambda started processing")

    try:
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        print(f"Bucket: {bucket}")
        print(f"File: {key}")

        response = s3.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')

        logs = []

        for line in content.splitlines():
            if line.strip():
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    print("Invalid log skipped")

        print(f"✅ Total logs parsed: {len(logs)}")

        # 🚨 Rule 1
        failed_count = {}

        for log in logs:
            if log.get("status") == "failure":
                key = (log.get("username"), log.get("ip"))
                failed_count[key] = failed_count.get(key, 0) + 1

        for (username, ip), count in failed_count.items():
            if count >= 3:
                print("🚨 ALERT: Multiple failed logins detected!")
                print(f"User: {username}, IP: {ip}, Attempts: {count}")

        return {"statusCode": 200}

    except Exception as e:
        print("Error:", str(e))
        return {"statusCode": 500}