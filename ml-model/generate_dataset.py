import random
import pandas as pd
import numpy as np

def generate_dataset(size=2000):
    data = []
    
    num_normal = int(size * 0.7)
    num_anomalies = size - num_normal
    
    # --- Generate NORMAL Data (70%) ---
    for _ in range(num_normal):
        login_hour = random.randint(8, 20)
        failed_attempts = random.randint(0, 2)
        ip_count = random.randint(1, 2)
        failure_ratio = round(random.uniform(0, 0.3), 2)
        
        data.append([login_hour, failed_attempts, ip_count, failure_ratio])
        
    # --- Generate ANOMALOUS Data (30%) ---
    for _ in range(num_anomalies):
        pattern = random.choice(["brute_force", "credential_stuffing", "bot_attack", "night_owl"])
        
        if pattern == "brute_force":
            login_hour = random.randint(0, 23)
            failed_attempts = random.randint(10, 30)
            ip_count = random.randint(1, 3)
            failure_ratio = round(random.uniform(0.8, 1.0), 2)
            
        elif pattern == "credential_stuffing":
            login_hour = random.randint(0, 23)
            failed_attempts = random.randint(5, 15)
            ip_count = random.randint(5, 15)
            failure_ratio = round(random.uniform(0.4, 0.7), 2)
            
        elif pattern == "bot_attack":
            login_hour = random.randint(0, 23)
            failed_attempts = random.randint(15, 50)
            ip_count = random.randint(8, 20)
            failure_ratio = round(random.uniform(0.7, 1.0), 2)
            
        else: # night_owl / general anomaly
            login_hour = random.randint(0, 5)
            failed_attempts = random.randint(3, 10)
            ip_count = random.randint(2, 5)
            failure_ratio = round(random.uniform(0.5, 0.8), 2)
            
        data.append([login_hour, failed_attempts, ip_count, failure_ratio])
        
    # Create DataFrame and Shuffle
    df = pd.DataFrame(data, columns=[
        "login_hour",
        "failed_attempts",
        "ip_count",
        "failure_ratio"
    ])
    df = df.sample(frac=1).reset_index(drop=True)
    
    # Save as dataset.csv
    df.to_csv("dataset.csv", index=False)
    print(f"✅ Dataset generated: dataset.csv ({len(df)} rows)")

if __name__ == "__main__":
    generate_dataset(size=2000)