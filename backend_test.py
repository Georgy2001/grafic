#!/usr/bin/env python3
"""
Backend API Testing for Shift Schedule Manager
Tests all API endpoints with proper authentication flow
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ShiftScheduleAPITester:
    def __init__(self, base_url: str = "https://61666eee-da01-490c-b3c3-791589cd2e4c.preview.emergentagent.com"):
        self.base_url = base_url
        self.manager_token = None
        self.employee_token = None
        self.created_employee_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.session = requests.Session()
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        return success

    def api_call(self, method: str, endpoint: str, data: Optional[Dict] = None, 
                 token: Optional[str] = None, expected_status: int = 200) -> tuple[bool, Dict]:
        """Make API call and return success status and response data"""
        url = f"{self.base_url}/api{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if token:
            headers['Authorization'] = f'Bearer {token}'
            
        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=headers)
            else:
                return False, {"error": f"Unsupported method: {method}"}
                
            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text, "status_code": response.status_code}
                
            return success, response_data
            
        except Exception as e:
            return False, {"error": str(e)}

    def test_health_check(self) -> bool:
        """Test health endpoint"""
        success, data = self.api_call('GET', '/health')
        return self.log_test("Health Check", success, 
                           f"- Status: {data.get('status', 'unknown')}")

    def test_manager_login(self) -> bool:
        """Test manager login with default credentials"""
        login_data = {
            "email": "manager@company.com",
            "password": "manager123"
        }
        
        success, data = self.api_call('POST', '/auth/login', login_data)
        
        # Debug output
        print(f"DEBUG: Login response - Success: {success}, Data: {data}")
        
        if success and 'access_token' in data:
            self.manager_token = data['access_token']
            user_info = data.get('user', {})
            return self.log_test("Manager Login", True, 
                               f"- Role: {user_info.get('role')}, Name: {user_info.get('name')}")
        else:
            return self.log_test("Manager Login", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_invalid_login(self) -> bool:
        """Test login with invalid credentials"""
        login_data = {
            "email": "invalid@test.com",
            "password": "wrongpassword"
        }
        
        success, data = self.api_call('POST', '/auth/login', login_data, expected_status=401)
        return self.log_test("Invalid Login", success, 
                           f"- Correctly rejected with: {data.get('detail', 'No error message')}")

    def test_get_current_user(self) -> bool:
        """Test getting current user info"""
        if not self.manager_token:
            return self.log_test("Get Current User", False, "- No manager token available")
            
        success, data = self.api_call('GET', '/auth/me', token=self.manager_token)
        return self.log_test("Get Current User", success, 
                           f"- User: {data.get('name', 'Unknown')}, Role: {data.get('role', 'Unknown')}")

    def test_create_employee(self) -> bool:
        """Test creating a new employee"""
        if not self.manager_token:
            return self.log_test("Create Employee", False, "- No manager token available")
            
        employee_data = {
            "email": f"test_employee_{datetime.now().strftime('%H%M%S')}@company.com",
            "name": "Test Employee",
            "password": "employee123",
            "role": "employee"
        }
        
        success, data = self.api_call('POST', '/auth/register', employee_data, 
                                    token=self.manager_token, expected_status=200)
        
        # Debug output
        print(f"DEBUG: Create employee response - Success: {success}, Data: {data}")
        
        if success and 'user' in data:
            self.created_employee_id = data['user']['id']
            return self.log_test("Create Employee", True, 
                               f"- Created: {data['user']['name']} (ID: {self.created_employee_id})")
        else:
            return self.log_test("Create Employee", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_employee_login(self) -> bool:
        """Test login with created employee"""
        if not self.created_employee_id:
            return self.log_test("Employee Login", False, "- No employee created")
            
        # Get employee email from the creation test
        employee_email = f"test_employee_{datetime.now().strftime('%H%M%S')}@company.com"
        
        login_data = {
            "email": employee_email,
            "password": "employee123"
        }
        
        success, data = self.api_call('POST', '/auth/login', login_data)
        
        if success and 'access_token' in data:
            self.employee_token = data['access_token']
            return self.log_test("Employee Login", True, 
                               f"- Employee logged in successfully")
        else:
            return self.log_test("Employee Login", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_get_users_as_manager(self) -> bool:
        """Test getting users list as manager"""
        if not self.manager_token:
            return self.log_test("Get Users (Manager)", False, "- No manager token available")
            
        success, data = self.api_call('GET', '/users', token=self.manager_token)
        
        # Debug output
        print(f"DEBUG: Get users response - Success: {success}, Data: {data}")
        
        if success and isinstance(data, list):
            return self.log_test("Get Users (Manager)", True, 
                               f"- Found {len(data)} users")
        else:
            return self.log_test("Get Users (Manager)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_get_users_as_employee(self) -> bool:
        """Test getting users list as employee (should fail)"""
        if not self.employee_token:
            return self.log_test("Get Users (Employee)", False, "- No employee token available")
            
        success, data = self.api_call('GET', '/users', token=self.employee_token, expected_status=403)
        return self.log_test("Get Users (Employee)", success, 
                           f"- Correctly forbidden: {data.get('detail', 'No error message')}")

    def test_create_schedule(self) -> bool:
        """Test creating a schedule"""
        if not self.manager_token or not self.created_employee_id:
            return self.log_test("Create Schedule", False, "- Missing manager token or employee ID")
            
        current_date = datetime.now()
        schedule_data = {
            "month": current_date.month,
            "year": current_date.year,
            "shifts": [
                {
                    "date": f"{current_date.year}-{current_date.month:02d}-01",
                    "type": "day",
                    "assignments": [
                        {
                            "employee_id": self.created_employee_id,
                            "employee_name": "Test Employee"
                        }
                    ],
                    "hours": None,
                    "notes": "Test shift"
                },
                {
                    "date": f"{current_date.year}-{current_date.month:02d}-02",
                    "type": "night",
                    "assignments": [
                        {
                            "employee_id": self.created_employee_id,
                            "employee_name": "Test Employee"
                        }
                    ],
                    "hours": None,
                    "notes": "Night shift test"
                }
            ]
        }
        
        success, data = self.api_call('POST', '/schedules', schedule_data, 
                                    token=self.manager_token, expected_status=200)
        
        if success and 'schedule' in data:
            return self.log_test("Create Schedule", True, 
                               f"- Created schedule with {len(data['schedule']['shifts'])} shifts")
        else:
            return self.log_test("Create Schedule", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_get_schedule(self) -> bool:
        """Test getting schedule"""
        if not self.manager_token:
            return self.log_test("Get Schedule", False, "- No manager token available")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', f'/schedules/{current_date.year}/{current_date.month}', 
                                    token=self.manager_token)
        
        if success and 'schedule' in data:
            schedule = data['schedule']
            if schedule:
                return self.log_test("Get Schedule", True, 
                                   f"- Found schedule with {len(schedule.get('shifts', []))} shifts")
            else:
                return self.log_test("Get Schedule", True, "- No schedule found (empty)")
        else:
            return self.log_test("Get Schedule", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_get_my_shifts(self) -> bool:
        """Test getting employee's shifts"""
        if not self.employee_token:
            return self.log_test("Get My Shifts", False, "- No employee token available")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', f'/my-shifts/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token)
        
        if success and 'shifts' in data and 'stats' in data:
            shifts = data['shifts']
            stats = data['stats']
            return self.log_test("Get My Shifts", True, 
                               f"- Found {len(shifts)} shifts, Total hours: {stats.get('total_hours', 0)}")
        else:
            return self.log_test("Get My Shifts", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_delete_employee(self) -> bool:
        """Test deleting the created employee"""
        if not self.manager_token or not self.created_employee_id:
            return self.log_test("Delete Employee", False, "- Missing manager token or employee ID")
            
        success, data = self.api_call('DELETE', f'/users/{self.created_employee_id}', 
                                    token=self.manager_token)
        
        return self.log_test("Delete Employee", success, 
                           f"- {data.get('message', data.get('detail', 'Unknown result'))}")

    def run_all_tests(self) -> int:
        """Run all tests in sequence"""
        print("🚀 Starting Shift Schedule Manager API Tests")
        print("=" * 60)
        
        # Basic connectivity tests
        self.test_health_check()
        
        # Authentication tests
        self.test_manager_login()
        self.test_invalid_login()
        self.test_get_current_user()
        
        # User management tests
        self.test_create_employee()
        self.test_employee_login()
        self.test_get_users_as_manager()
        self.test_get_users_as_employee()
        
        # Schedule management tests
        self.test_create_schedule()
        self.test_get_schedule()
        self.test_get_my_shifts()
        
        # Cleanup
        self.test_delete_employee()
        
        # Print summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return 0
        else:
            print(f"⚠️  {self.tests_run - self.tests_passed} tests failed")
            return 1

def main():
    """Main test runner"""
    tester = ShiftScheduleAPITester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())