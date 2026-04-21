import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

def get_dynamodb():
    try:
        sts = boto3.client('sts', region_name='us-east-1')
        print(f"Logged in as: {sts.get_caller_identity()['Arn']}")
    except Exception as e:
        print(f"AWS connection error. Make sure you are using Admin credentials or CloudShell: {e}")
        return None
    return boto3.resource('dynamodb', region_name='us-east-1')

def create_table(dynamodb, table_name, key_schema, attribute_definitions, global_secondary_indexes=None):
    try:
        print(f"Checking if {table_name} exists...")
        table = dynamodb.Table(table_name)
        table.load()
        print(f"Table {table_name} already exists. Deleting it to apply new schema...")
        table.delete()
        table.meta.client.get_waiter('table_not_exists').wait(TableName=table_name)
        print(f"Deleted {table_name}.")
    except ClientError as e:
        if e.response['Error']['Code'] != 'ResourceNotFoundException':
            print(f"Error checking table: {e}")
            return
            
    print(f"Creating table {table_name}...")
    params = {
        'TableName': table_name,
        'KeySchema': key_schema,
        'AttributeDefinitions': attribute_definitions,
        'BillingMode': 'PAY_PER_REQUEST'
    }
    if global_secondary_indexes:
        params['GlobalSecondaryIndexes'] = global_secondary_indexes
        
    try:
        table = dynamodb.create_table(**params)
        table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
        print(f"[OK] Executed. Table {table_name} status is {table.table_status}")
    except Exception as e:
        print(f"[ERROR] Failed to create {table_name}: {e}")

def main():
    ddb = get_dynamodb()
    if not ddb:
        return
        
    print("\n--- TASK 1: Provisioning SIEM Multi-Tenant DynamoDB Database ---")
    
    # Table 1: Companies
    create_table(
        ddb, 'Companies',
        [{'AttributeName': 'company_id', 'KeyType': 'HASH'}],
        [{'AttributeName': 'company_id', 'AttributeType': 'S'}]
    )

    # Table 2: SecurityAlerts
    create_table(
        ddb, 'SecurityAlerts',
        [
            {'AttributeName': 'id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        [
            {'AttributeName': 'id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'},
            {'AttributeName': 'company_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'company_id-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'company_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )

    # Table 3: ProcessedLogs
    create_table(
        ddb, 'ProcessedLogs',
        [
            {'AttributeName': 'log_id', 'KeyType': 'HASH'},
            {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
        ],
        [
            {'AttributeName': 'log_id', 'AttributeType': 'S'},
            {'AttributeName': 'timestamp', 'AttributeType': 'S'},
            {'AttributeName': 'company_id', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'company_id-timestamp-index',
                'KeySchema': [
                    {'AttributeName': 'company_id', 'KeyType': 'HASH'},
                    {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    )
    print("\n[OK] Task 1 DynamoDB Construction Complete!")

if __name__ == '__main__':
    main()
