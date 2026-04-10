import random
import pandas as pd

data = []

for _ in range(2000):
    login_hour = random.randint(8, 22)  # typical working hours
    
    failed_attempts = random.randint(0, 2)  # normal users rarely fail
    
    ip_count = random.randint(1, 2)  # usually same device/IP
    
    failure_ratio = round(random.uniform(0, 0.3), 2)

    data.append([
        login_hour,
        failed_attempts,
        ip_count,
        failure_ratio
    ])

df = pd.DataFrame(data, columns=[
    "login_hour",
    "failed_attempts",
    "ip_count",
    "failure_ratio"
])


df.to_csv("baseline.csv", index=False)

print("✅ baseline.csv created successfully")