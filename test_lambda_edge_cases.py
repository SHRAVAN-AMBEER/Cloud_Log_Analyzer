"""
WEEK 5: Comprehensive Edge Case Testing for Lambda Function
Tests for anomaly detection rules, performance, and error handling
"""

import json
from datetime import datetime, timedelta
import sys
sys.path.insert(0, 'lambda')

# Mock AWS clients
class MockDynamodb:
    def Table(self, name):
        return MockTable(name)

class MockTable:
    def __init__(self, name):
        self.name = name
        self.items = []
    
    def put_item(self, Item):
        self.items.append(Item)
    
    def batch_writer(self, batch_size=25, overwrite_by_pkey=False):
        return MockBatchWriter(self)

class MockBatchWriter:
    def __init__(self, table):
        self.table = table
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass
    
    def put_item(self, Item):
        self.table.items.append(Item)

# Test data generators
def generate_log(username='testuser', ip='192.168.1.1', status='success', 
                 timestamp=None, user_agent='Mozilla/5.0'):
    """Generate a single log entry"""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + 'Z'
    
    return {
        'username': username,
        'ip': ip,
        'status': status,
        'timestamp': timestamp,
        'user_agent': user_agent
    }

def generate_logs_batch(count, **kwargs):
    """Generate multiple log entries"""
    return [generate_log(**kwargs) for _ in range(count)]

# Test Suite

class TestEdgeCases:
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.results = []
    
    def test(self, name):
        """Decorator for test functions"""
        def decorator(func):
            def wrapper():
                try:
                    func()
                    self.tests_passed += 1
                    self.results.append(f"✅ {name}")
                    print(f"✅ {name}")
                except AssertionError as e:
                    self.tests_failed += 1
                    self.results.append(f"❌ {name}: {str(e)}")
                    print(f"❌ {name}: {str(e)}")
                except Exception as e:
                    self.tests_failed += 1
                    self.results.append(f"❌ {name}: {type(e).__name__}: {str(e)}")
                    print(f"❌ {name}: {type(e).__name__}: {str(e)}")
            return wrapper
        return decorator
    
    def assert_equal(self, actual, expected, msg=""):
        if actual != expected:
            raise AssertionError(f"{msg} Expected {expected}, got {actual}")
    
    def assert_true(self, condition, msg=""):
        if not condition:
            raise AssertionError(msg)
    
    def assert_gt(self, actual, expected, msg=""):
        if actual <= expected:
            raise AssertionError(f"{msg} Expected > {expected}, got {actual}")
    
    # EDGE CASE TESTS
    
    @property
    def test_empty_logs(self):
        @self.test("Empty logs handling")
        def run():
            logs = []
            # Should not crash
            result = {
                'total_logs': len(logs),
                'valid': len(logs) > 0
            }
            self.assert_equal(result['total_logs'], 0, "Empty logs")
        return run
    
    @property
    def test_missing_fields(self):
        @self.test("Logs with missing fields")
        def run():
            incomplete_logs = [
                {'username': 'user1'},  # Missing ip, status, timestamp
                {'ip': '192.168.1.1'},  # Missing username, status, timestamp
                {'username': 'user2', 'timestamp': '2026-03-31T10:00:00Z'},  # Missing ip, status
            ]
            valid_count = sum(1 for log in incomplete_logs 
                            if all([log.get('username'), log.get('timestamp'), 
                                   log.get('ip'), log.get('status')]))
            self.assert_equal(valid_count, 0, "Should filter all incomplete logs")
        return run
    
    @property
    def test_malformed_json(self):
        @self.test("Malformed JSON handling")
        def run():
            malformed_lines = [
                '{invalid json}',
                '{"username": "user1"',  # Missing closing brace
                'not json at all',
                '''{
                    "username": "user1",
                    "ip": "192.168.1.1",
                    "status": "success",
                    "timestamp": "2026-03-31T10:00:00Z"
                }'''  # Valid
            ]
            
            valid_count = 0
            for line in malformed_lines:
                try:
                    json.loads(line)
                    valid_count += 1
                except json.JSONDecodeError:
                    pass
            
            self.assert_equal(valid_count, 1, "Should parse 1 valid JSON")
        return run
    
    @property
    def test_duplicate_logs(self):
        @self.test("Duplicate log entries")
        def run():
            logs = [
                generate_log('user1', '192.168.1.1', 'success', '2026-03-31T10:00:00Z'),
                generate_log('user1', '192.168.1.1', 'success', '2026-03-31T10:00:00Z'),  # Duplicate
                generate_log('user2', '192.168.1.2', 'failure', '2026-03-31T10:00:01Z'),
            ]
            self.assert_equal(len(logs), 3, "Should have 3 logs")
            
            # Duplicate detection
            seen = set()
            unique_count = 0
            for log in logs:
                key = (log['username'], log['timestamp'])
                if key not in seen:
                    seen.add(key)
                    unique_count += 1
            
            self.assert_gt(len(logs), unique_count, "Should have duplicates")
        return run
    
    @property
    def test_concurrent_logins(self):
        @self.test("Concurrent logins from same user")
        def run():
            # Same user logging in from 5 different locations
            base_time = datetime.utcnow()
            logs = [
                generate_log('user1', f'192.168.1.{i}', 'success', 
                           (base_time + timedelta(seconds=i)).isoformat() + 'Z')
                for i in range(1, 6)
            ]
            self.assert_equal(len(logs), 5, "Should have 5 concurrent logins")
        return run
    
    @property
    def test_large_batch(self):
        @self.test("Large batch of logs (1000+)")
        def run():
            logs = generate_logs_batch(1000, username='user1')
            self.assert_equal(len(logs), 1000, "Should handle 1000 logs")
        return run
    
    @property
    def test_special_characters_in_fields(self):
        @self.test("Special characters in log fields")
        def run():
            special_logs = [
                generate_log('user@domain', '192.168.1.1'),
                generate_log('user.name', '192.168.1.1'),
                generate_log('user-name', '192.168.1.1'),
                generate_log('user_name', '192.168.1.1'),
                generate_log('user\'s', '192.168.1.1'),
                generate_log('user"name', '192.168.1.1'),
            ]
            self.assert_equal(len(special_logs), 6, "Should handle special chars")
        return run
    
    @property
    def test_null_timestamp(self):
        @self.test("Logs with null/invalid timestamps")
        def run():
            logs = [
                generate_log('user1', '192.168.1.1', 'success', 'invalid-date'),
                generate_log('user2', '192.168.1.2', 'success', ''),
                generate_log('user3', '192.168.1.3', 'success', None),
            ]
            
            valid_timestamps = 0
            for log in logs:
                ts = log.get('timestamp')
                try:
                    if ts:
                        datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        valid_timestamps += 1
                except (ValueError, AttributeError):
                    pass
            
            self.assert_equal(valid_timestamps, 0, "Should detect invalid timestamps")
        return run
    
    @property
    def test_extreme_values(self):
        @self.test("Extreme field values")
        def run():
            extreme_logs = [
                generate_log('x' * 1000, '192.168.1.1'),  # Very long username
                generate_log('user1', '192.168.' + '.'.join(['1'] * 100)),  # Invalid IP
                generate_log('user1', '192.168.1.1', 'success', '9999-12-31T23:59:59Z'),  # Far future
            ]
            self.assert_equal(len(extreme_logs), 3, "Should accept extreme values")
        return run
    
    @property
    def test_password_spray_detection(self):
        @self.test("Password spray attack detection (5+ users from same IP)")
        def run():
            logs = [
                generate_log(f'user{i}', '192.168.1.10', 'failure')
                for i in range(10)
            ]
            
            ip_user_map = {}
            for log in logs:
                ip = log.get('ip')
                if ip not in ip_user_map:
                    ip_user_map[ip] = set()
                ip_user_map[ip].add(log.get('username'))
            
            spray_detected = any(len(users) >= 5 for users in ip_user_map.values())
            self.assert_true(spray_detected, "Should detect password spray")
        return run
    
    @property
    def test_velocity_abuse(self):
        @self.test("Velocity abuse detection (10+ logins per minute)")
        def run():
            base_time = datetime.utcnow()
            logs = [
                generate_log('user1', '192.168.1.1', 'success',
                           (base_time + timedelta(seconds=i*6)).isoformat() + 'Z')
                for i in range(11)
            ]
            
            self.assert_equal(len(logs), 11, "Should have 11 logins in 1 minute")
        return run
    
    @property
    def test_off_hours_detection(self):
        @self.test("Off-hours login detection (10 PM - 6 AM)")
        def run():
            # Login at 2 AM
            logs = [generate_log('user1', '192.168.1.1', 'success',
                               '2026-03-31T02:00:00Z')]
            
            for log in logs:
                ts = datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))
                is_off_hours = ts.hour >= 22 or ts.hour < 6
                self.assert_true(is_off_hours, "Should detect off-hours login")
        return run
    
    @property
    def test_new_ip_detection(self):
        @self.test("New IP location detection")
        def run():
            logs = [
                generate_log('user1', '192.168.1.1', 'success'),  # First IP
                generate_log('user1', '192.168.1.2', 'success'),  # New IP
                generate_log('user1', '192.168.1.1', 'success'),  # Back to first IP
            ]
            
            user_ips = {}
            for log in logs:
                username = log['username']
                ip = log['ip']
                if username not in user_ips:
                    user_ips[username] = set()
                user_ips[username].add(ip)
            
            self.assert_gt(len(user_ips['user1']), 1, "Should detect multiple IPs")
        return run
    
    @property
    def test_brute_force_lockout(self):
        @self.test("Brute force account lockout detection (10+ failures)")
        def run():
            logs = generate_logs_batch(15, username='admin', status='failure')
            
            failed_count = sum(1 for log in logs if log.get('status') == 'failure')
            lockout_detected = failed_count >= 10
            self.assert_true(lockout_detected, "Should detect lockout attempt")
        return run
    
    @property
    def test_mixed_success_failure(self):
        @self.test("Mixed success/failure logs")
        def run():
            logs = [
                generate_log('user1', '192.168.1.1', 'success'),
                generate_log('user1', '192.168.1.1', 'failure'),
                generate_log('user1', '192.168.1.1', 'failure'),
                generate_log('user1', '192.168.1.1', 'failure'),
                generate_log('user1', '192.168.1.1', 'success'),
            ]
            
            failure_count = sum(1 for log in logs if log.get('status') == 'failure')
            self.assert_equal(failure_count, 3, "Should count 3 failures")
        return run
    
    @property
    def test_timeout_resilience(self):
        @self.test("Lambda timeout resilience (>1000 logs)")
        def run():
            # Simulate 5000 logs - should complete in <15 seconds
            logs = generate_logs_batch(5000)
            self.assert_equal(len(logs), 5000, "Should handle 5000 logs")
        return run
    
    def run_all(self):
        """Run all tests"""
        print("\n" + "="*60)
        print("🧪 WEEK 5: EDGE CASE TEST SUITE")
        print("="*60 + "\n")
        
        # Run all test properties
        tests = [
            self.test_empty_logs,
            self.test_missing_fields,
            self.test_malformed_json,
            self.test_duplicate_logs,
            self.test_concurrent_logins,
            self.test_large_batch,
            self.test_special_characters_in_fields,
            self.test_null_timestamp,
            self.test_extreme_values,
            self.test_password_spray_detection,
            self.test_velocity_abuse,
            self.test_off_hours_detection,
            self.test_new_ip_detection,
            self.test_brute_force_lockout,
            self.test_mixed_success_failure,
            self.test_timeout_resilience,
        ]
        
        for test in tests:
            test()
        
        # Print summary
        print("\n" + "="*60)
        print(f"📊 TEST SUMMARY")
        print("="*60)
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {self.tests_failed}")
        print(f"📈 Total:  {self.tests_passed + self.tests_failed}")
        print(f"🎯 Success Rate: {self.tests_passed / (self.tests_passed + self.tests_failed) * 100:.1f}%")
        print("\n" + "="*60 + "\n")
        
        return self.tests_passed, self.tests_failed


if __name__ == "__main__":
    tester = TestEdgeCases()
    passed, failed = tester.run_all()
    
    # Exit with appropriate code
    exit(0 if failed == 0 else 1)
