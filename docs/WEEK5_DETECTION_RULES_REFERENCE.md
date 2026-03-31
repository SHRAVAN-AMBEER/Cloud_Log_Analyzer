# 🎯 WEEK 5 - Detection Rules Quick Reference

## 7 Detection Rules at a Glance

```
┌─────────────────────────────────────────────────────────────┐
│         WEEK 5 ANOMALY DETECTION RULES MATRIX               │
└─────────────────────────────────────────────────────────────┘
```

### Rule 1: Multiple Failed Logins ⚠️

**What triggers it:**
```
Same user + IP = 3+ failed attempts
```

**Real Example:**
```
❌ user: admin, ip: 192.168.1.100 fails 5 times
   → ALERT: MULTIPLE_FAILED_LOGINS, severity: HIGH
```

**Parameters:**
```
THRESHOLD: 3 failures
WINDOW: Entire batch
SEVERITY: MEDIUM (3) → HIGH (5) → CRITICAL (10+)
```

**What to do:**
- Check if account compromised
- Verify IP legitimacy  
- Consider temporary block

---

### Rule 2: Password Spray Attack 🎯

**What triggers it:**
```
Same IP + 5+ different users = spray attack
```

**Real Example:**
```
❌ ip: 203.0.113.50 tries to login as:
   - john ❌
   - admin ❌
   - root ❌
   - test ❌
   - user1 ❌
   - user2 ❌ (6 users total)
   → ALERT: PASSWORD_SPRAY, severity: CRITICAL
```

**Parameters:**
```
THRESHOLD: 5 users
PATTERN: Different users, same IP, failures
SEVERITY: HIGH (5) → CRITICAL (10+)
```

**What to do:**
- Block IP immediately
- Check if any accounts compromised
- Monitor for follow-up attacks

---

### Rule 3: Velocity Abuse 🚀

**What triggers it:**
```
Single user: 10+ logins in 1 minute
```

**Real Example:**
```
❌ user: john.doe logs in at:
   - 10:00:01 ✓
   - 10:00:06 ✓
   - 10:00:11 ✓
   ... (12 times in 60 seconds)
   → ALERT: VELOCITY_ABUSE, severity: HIGH
```

**Parameters:**
```
THRESHOLD: 10 logins/minute/user
WINDOW: 60 seconds sliding
SEVERITY: HIGH (10+) → CRITICAL (20+)
```

**What to do:**
- Likely bot/credential stuffing attack
- Block account temporarily
- Reset password immediately
- Check for data exfiltration

---

### Rule 4: Unusual Time Login ⏰

**What triggers it:**
```
Successful login at off-hours + 2+ times
Off-hours: 10 PM to 6 AM (22:00 - 06:00)
```

**Real Example:**
```
✓ user: manager logs in at:
   - 2:34 AM (off-hours) ⏰
   - 3:12 AM (off-hours) ⏰
   → ALERT: UNUSUAL_TIME_LOGIN, severity: MEDIUM
```

**Parameters:**
```
OFF-HOURS: 22:00 - 06:00
THRESHOLD: 2+ logins
SEVERITY: LOW (2) → MEDIUM (3+)
```

**What to do:**
- Verify if legitimate (rotating shift?)
- Check if account compromised
- Low severity but monitor pattern

**Note:** This rule is optional—adjust off-hours based on your org

---

### Rule 5: Repeated Failed Attempts ⚡

**What triggers it:**
```
5+ failures within 15-minute TIME WINDOW
(More sophisticated than simple count)
```

**Real Example:**
```
❌ user: sarah, ip: 192.168.1.50
   - 10:00 AM: failure
   - 10:02 AM: failure
   - 10:05 AM: failure
   - 10:08 AM: failure
   - 10:12 AM: failure
   - 10:14 AM: failure (6 failures in 14 minutes)
   → ALERT: REPEATED_FAILED_ATTEMPTS, severity: HIGH
```

**Parameters:**
```
THRESHOLD: 5+ failures
WINDOW: 15 minutes
SEVERITY: HIGH (5) → CRITICAL (10+)
```

**What to do:**
- Rapid-fire brute force attack
- Implement rate limiting
- Consider account lockout
- IP reputation check

---

### Rule 6: New Location Login 📍

**What triggers it:**
```
User successfully logs in from NEW IP
(Only alerts if user has history)
```

**Real Example:**
```
✓ user: sarah always logs from: 10.0.0.50
  New login from: 203.0.113.100 🚨
  → ALERT: NEW_LOCATION, severity: LOW
```

**Parameters:**
```
CONDITION: User has prior login history
ALERT: Any new successful IP
SEVERITY: LOW → MEDIUM (if multiple new IPs)
```

**What to do:**
- Low severity—monitor pattern
- Could be legitimate (WFH, travel)
- High priority if matched with other rules

---

### Rule 7: Account Lockout Pattern 🔒

**What triggers it:**
```
Single user: 10+ failed attempts
(Indicates someone trying to lock them out)
```

**Real Example:**
```
❌ user: admin receives 15 failed attempts
        from IP: 192.168.1.200
   → ALERT: ACCOUNT_LOCKOUT_ATTEMPT, severity: HIGH
```

**Parameters:**
```
THRESHOLD: 10+ failures per user
ATTACK_TYPE: Brute force lockout attempt
SEVERITY: HIGH (10) → CRITICAL (20+)
```

**What to do:**
- Immediately notify user
- Temporarily lock account
- Implement rate limiting
- Investigate if real login attempts

---

## 🎛️ Severity Legend

```
CRITICAL 🔴
├─ Immediate action required
├─ Investigate within minutes
└─ Examples: 20+ failures, impossible travel, active exploits

HIGH 🟠
├─ Serious concern
├─ Investigate within hours
└─ Examples: 5+ failures, password spray

MEDIUM 🟡
├─ Monitor
├─ Investigate within day
└─ Examples: 3 failures, unusual time logins

LOW 🟢
├─ Informational
├─ Review weekly
└─ Examples: New location, pattern changes
```

---

## 🔄 Rule Correlation Examples

### Scenario 1: Brute Force Attack
```
TRIGGERS:
✓ Rule 2: Password spray (IP 203.0.113.50 tries 8 users)
✓ Rule 1: Multiple failed logins (5 attempts on admin)
✓ Rule 7: Account lockout (admin gets 12 failures)

ACTION: 🔴 CRITICAL - Block IP, alert team immediately
```

### Scenario 2: Insider Threat
```
TRIGGERS:
✓ Rule 4: Unusual time (Manager logs in 3x at 2 AM)
✓ Rule 6: New location (New IP from known user)
✓ Rule 3: Velocity (20 logins in 5 minutes)

ACTION: 🟠 HIGH - Investigate access logs, check data access
```

### Scenario 3: Compromised Account
```
TRIGGERS:
✓ Rule 5: Repeated failures (5 failures in 10 min)
✓ Rule 3: Velocity abuse (12 logins in 60 sec)
✓ Rule 6: New location (New IP first time)

ACTION: 🟠 HIGH - Force password reset, revoke sessions
```

### Scenario 4: Normal Activity
```
TRIGGERS:
✓ Rule 6: New location (Traveling, WiFi login)
✗ No other rules triggered

ACTION: 🟢 LOW - Monitor only, likely legitimate
```

---

## 📊 Alert Tuning Guide

### Too Many False Positives?

**Problem**: Getting alerts for normal users traveling

**Solution**: Adjust parameters
```python
# Increase thresholds
FAILED_LOGIN_THRESHOLD = 5  # Was 3
TIME_WINDOW_MINUTES = 30    # Was 15

# Or disable Rule 6 (new location)
# Or whitelist certain IPs
```

### Missing Real Attacks?

**Problem**: Not catching some attacks

**Solution**: Lower thresholds
```python
FAILED_LOGIN_THRESHOLD = 2
PASSWORD_SPRAY_THRESHOLD = 3
MAX_LOGINS_PER_MINUTE = 5
```

### Rule Not Firing?

**Debug Checklist:**
```
□ Check if condition is met
□ Verify threshold value
□ Check log format (has all required fields?)
□ Test with manual logs
□ Check Lambda logs in CloudWatch
```

---

## 🧪 Testing Each Rule

### Test Data for Each Rule

```python
# Rule 1: Multiple Failed Logins
test_logs = [
    {'username': 'admin', 'ip': '192.168.1.1', 'status': 'failure', 'timestamp': '...'},
    {'username': 'admin', 'ip': '192.168.1.1', 'status': 'failure', 'timestamp': '...'},
    {'username': 'admin', 'ip': '192.168.1.1', 'status': 'failure', 'timestamp': '...'},
    # Should trigger: 3 failures = ALERT
]

# Rule 2: Password Spray
test_logs = [
    {'username': 'user1', 'ip': '203.0.113.50', 'status': 'failure', 'timestamp': '...'},
    {'username': 'user2', 'ip': '203.0.113.50', 'status': 'failure', 'timestamp': '...'},
    {'username': 'user3', 'ip': '203.0.113.50', 'status': 'failure', 'timestamp': '...'},
    {'username': 'user4', 'ip': '203.0.113.50', 'status': 'failure', 'timestamp': '...'},
    {'username': 'user5', 'ip': '203.0.113.50', 'status': 'failure', 'timestamp': '...'},
    # Should trigger: 5 users from same IP = ALERT
]

# ... etc for other rules
```

---

## 📈 Metrics to Monitor

```
Daily Tracking:
├─ Total logins processed
├─ Alerts by severity (CRITICAL/HIGH/MEDIUM/LOW)
├─ False positive rate
├─ Most common alert type
└─ IPs/Users with most alerts
```

---

## ⚙️ Configuration Template

Use this in your Lambda environment variables:

```bash
FAILED_LOGIN_THRESHOLD=3
PASSWORD_SPRAY_THRESHOLD=5
TIME_WINDOW_MINUTES=15
MAX_LOGINS_PER_MINUTE=10
BATCH_SIZE=25

# Optional: Region for geolocation
AWS_REGION=us-east-1
```

---

## 🚀 Deployment Checklist

Before deploying to production:

- [ ] All 7 rules tested with real logs
- [ ] Edge cases handled (malformed JSON, etc.)
- [ ] Performance tested (1000+ logs)
- [ ] CloudWatch alarms configured
- [ ] DynamoDB tables created
- [ ] IAM permissions verified
- [ ] Lambda timeout set to ≥60 seconds
- [ ] Memory set to ≥512 MB
- [ ] Test with actual S3 triggers

---

*WEEK 5 Complete! Your detection rules are PRODUCTION-READY.* ✨
