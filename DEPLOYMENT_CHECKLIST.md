# 📋 WEEK 5 DEPLOYMENT CHECKLIST

## Pre-Deployment (5 minutes)

- [ ] Have AWS Console access ready
- [ ] Know your S3 bucket name
- [ ] Region set to `us-east-1`
- [ ] Lambda function name: `log-analyzer-lambda`

---

## During Deployment (10 minutes)

### Code Upload
- [ ] Copy code from [LAMBDA_CODE_FOR_DEPLOYMENT.py](LAMBDA_CODE_FOR_DEPLOYMENT.py)
- [ ] Go to AWS Lambda console
- [ ] Open `log-analyzer-lambda` function
- [ ] Replace old code with new code
- [ ] Click **Deploy**
- [ ] Wait for: ✅ "Successfully updated function"

### Configuration
- [ ] Set Memory: **512 MB**
- [ ] Set Timeout: **60 seconds**
- [ ] Add 5 environment variables:
  - [ ] `BATCH_SIZE = 25`
  - [ ] `FAILED_LOGIN_THRESHOLD = 3`
  - [ ] `PASSWORD_SPRAY_THRESHOLD = 5`
  - [ ] `TIME_WINDOW_MINUTES = 15`
  - [ ] `MAX_LOGINS_PER_MINUTE = 10`
- [ ] Click **Save**

---

## Testing (5 minutes)

- [ ] Go to Lambda "Test" tab
- [ ] Create test event with your bucket name
- [ ] Click **Test**
- [ ] Check for ✅ green checkmark
- [ ] Verify response shows `"statusCode": 200`

---

## Verification (5 minutes)

### DynamoDB
- [ ] Open DynamoDB console
- [ ] Check `SecurityAlerts` table has items
- [ ] Check `ProcessedLogs` table has items
- [ ] Verify timestamps and data look correct

### CloudWatch Logs
- [ ] Lambda → Monitor → View logs
- [ ] See messages like "✅ Parsed X valid logs"
- [ ] No error messages visible

---

## Production Setup (Optional, 5 minutes)

- [ ] Add S3 trigger to Lambda
  - [ ] Click "Add trigger"
  - [ ] Select S3
  - [ ] Choose your bucket
  - [ ] Event: `s3:ObjectCreated:*`
  - [ ] Click "Add"
- [ ] Verify trigger is active

---

## Final Verification

- [ ] Code deployed: ✅
- [ ] Configuration set: ✅
- [ ] Test passed: ✅
- [ ] DynamoDB populated: ✅
- [ ] S3 trigger active: ✅
- [ ] CloudWatch logs clean: ✅

---

## 🎉 DEPLOYMENT COMPLETE!

**Your Lambda is now LIVE and ready to process logs automatically!**

---

## 📞 Quick Reference URLs

| Item | URL |
|------|-----|
| **Lambda Console** | https://console.aws.amazon.com/lambda/ |
| **DynamoDB Console** | https://console.aws.amazon.com/dynamodb/ |
| **CloudWatch Logs** | https://console.aws.amazon.com/logs/ |
| **S3 Console** | https://console.aws.amazon.com/s3/ |

---

## 🆘 If You Get Stuck

| Problem | Solution |
|---------|----------|
| **Code won't deploy** | Check syntax - Python may have formatting issue |
| **Can't find Lambda function** | Check region is set to `us-east-1` |
| **Test event fails** | Replace bucket name with YOUR actual S3 bucket |
| **No data in DynamoDB** | Create tables: SecurityAlerts, ProcessedLogs |
| **Permission errors** | Check Lambda execution role has DynamoDB permissions |

---

## 📈 Success Indicators

After deployment, you should see:
- ✅ Lambda execution time: ~1-3 seconds for 100-1000 logs
- ✅ DynamoDB: New items appearing
- ✅ CloudWatch: Clean logs with detection messages
- ✅ Zero errors in Lambda

---

## 🚀 NEXT STEPS (WEEK 6)

Once deployment verified:
1. Build Admin Dashboard
2. Set up email alerts for CRITICAL events
3. Implement auto-remediation
4. Add ML anomaly detection

---

**WEEK 5 DEPLOYMENT READY!** ✨
