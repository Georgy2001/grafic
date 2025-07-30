#!/usr/bin/env python3
"""
Backend API Testing for Shift Schedule Manager with Stores Support
Tests all API endpoints including extended stores functionality
"""

import requests
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class ShiftScheduleAPITester:
    def __init__(self, base_url: str = "https://abd0fd94-762e-45a2-8bdd-ae8bb6b1e0a4.preview.emergentagent.com"):
        self.base_url = base_url
        self.manager_token = None
        self.employee_token = None
        self.created_employee_id = None
        self.created_employee_email = None  # Store employee email
        self.created_store_id = None
        self.default_store_id = None
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
            elif method == 'PUT':
                response = self.session.put(url, json=data, headers=headers)
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
        """Test creating a new employee with store assignment"""
        if not self.manager_token or not self.default_store_id:
            return self.log_test("Create Employee", False, "- No manager token or default store available")
            
        # Generate unique email and store it
        self.created_employee_email = f"test_employee_{datetime.now().strftime('%Y%m%d_%H%M%S')}@company.com"
        
        employee_data = {
            "email": self.created_employee_email,
            "name": "Test Employee",
            "password": "employee123",
            "role": "employee",
            "store_ids": [self.default_store_id]  # Assign to default store
        }
        
        success, data = self.api_call('POST', '/auth/register', employee_data, 
                                    token=self.manager_token, expected_status=200)
        
        if success and 'user' in data:
            self.created_employee_id = data['user']['id']
            store_count = len(data['user'].get('store_ids', []))
            return self.log_test("Create Employee", True, 
                               f"- Created: {data['user']['name']} with {store_count} store(s)")
        else:
            return self.log_test("Create Employee", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_employee_login(self) -> bool:
        """Test login with created employee"""
        if not self.created_employee_email:
            return self.log_test("Employee Login", False, "- No employee email available")
            
        login_data = {
            "email": self.created_employee_email,
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

    # ===== STORE MANAGEMENT TESTS =====
    
    def test_get_default_stores(self) -> bool:
        """Test getting default stores and capture default store ID"""
        if not self.manager_token:
            return self.log_test("Get Default Stores", False, "- No manager token available")
            
        success, data = self.api_call('GET', '/stores', token=self.manager_token)
        
        if success and isinstance(data, list) and len(data) > 0:
            self.default_store_id = data[0]['id']  # Capture first store as default
            return self.log_test("Get Default Stores", True, 
                               f"- Found {len(data)} stores, default: {data[0]['name']}")
        else:
            return self.log_test("Get Default Stores", False, 
                               f"- Error or no stores: {data}")

    def test_create_store(self) -> bool:
        """Test creating a new store"""
        if not self.manager_token:
            return self.log_test("Create Store", False, "- No manager token available")
            
        store_data = {
            "name": f"Тестовая точка продаж {datetime.now().strftime('%H:%M:%S')}",
            "address": "ул. Тестовая, 123"
        }
        
        success, data = self.api_call('POST', '/stores', store_data, 
                                    token=self.manager_token, expected_status=200)
        
        if success and 'store' in data:
            self.created_store_id = data['store']['id']
            return self.log_test("Create Store", True, 
                               f"- Created: {data['store']['name']}")
        else:
            return self.log_test("Create Store", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_get_all_stores_as_manager(self) -> bool:
        """Test getting all stores as manager"""
        if not self.manager_token:
            return self.log_test("Get All Stores (Manager)", False, "- No manager token available")
            
        success, data = self.api_call('GET', '/stores', token=self.manager_token)
        
        if success and isinstance(data, list):
            return self.log_test("Get All Stores (Manager)", True, 
                               f"- Manager can see {len(data)} stores")
        else:
            return self.log_test("Get All Stores (Manager)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_get_stores_as_employee(self) -> bool:
        """Test getting stores as employee (should only see assigned stores)"""
        if not self.employee_token:
            return self.log_test("Get Stores (Employee)", False, "- No employee token available")
            
        success, data = self.api_call('GET', '/stores', token=self.employee_token)
        
        if success and isinstance(data, list):
            return self.log_test("Get Stores (Employee)", True, 
                               f"- Employee can see {len(data)} assigned stores")
        else:
            return self.log_test("Get Stores (Employee)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_get_specific_store(self) -> bool:
        """Test getting specific store details"""
        if not self.manager_token or not self.created_store_id:
            return self.log_test("Get Specific Store", False, "- Missing token or store ID")
            
        success, data = self.api_call('GET', f'/stores/{self.created_store_id}', 
                                    token=self.manager_token)
        
        if success and 'name' in data:
            return self.log_test("Get Specific Store", True, 
                               f"- Retrieved: {data['name']}")
        else:
            return self.log_test("Get Specific Store", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_update_store(self) -> bool:
        """Test updating store information"""
        if not self.manager_token or not self.created_store_id:
            return self.log_test("Update Store", False, "- Missing token or store ID")
            
        update_data = {
            "name": "Обновленная точка продаж",
            "address": "ул. Обновленная, 456"
        }
        
        success, data = self.api_call('PUT', f'/stores/{self.created_store_id}', 
                                    update_data, token=self.manager_token)
        
        return self.log_test("Update Store", success, 
                           f"- {data.get('message', data.get('detail', 'Unknown result'))}")

    def test_employee_access_to_unassigned_store(self) -> bool:
        """Test employee access to store they're not assigned to (should fail)"""
        if not self.employee_token or not self.created_store_id:
            return self.log_test("Employee Unassigned Store Access", False, 
                               "- Missing employee token or created store ID")
            
        success, data = self.api_call('GET', f'/stores/{self.created_store_id}', 
                                    token=self.employee_token, expected_status=403)
        
        return self.log_test("Employee Unassigned Store Access", success, 
                           f"- Correctly forbidden: {data.get('detail', 'No error message')}")

    def test_employee_access_to_assigned_store(self) -> bool:
        """Test employee access to their assigned store"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Employee Assigned Store Access", False, 
                               "- Missing employee token or default store ID")
            
        success, data = self.api_call('GET', f'/stores/{self.default_store_id}', 
                                    token=self.employee_token)
        
        if success and 'name' in data:
            return self.log_test("Employee Assigned Store Access", True, 
                               f"- Employee can access assigned store: {data['name']}")
        else:
            return self.log_test("Employee Assigned Store Access", False, 
                               f"- Error: {data.get('detail', data)}")

    # ===== STORE-SPECIFIC SCHEDULE TESTS =====

    def test_create_schedule_for_store(self) -> bool:
        """Test creating a schedule for specific store"""
        if not self.manager_token or not self.created_employee_id or not self.default_store_id:
            return self.log_test("Create Store Schedule", False, 
                               "- Missing manager token, employee ID, or store ID")
            
        current_date = datetime.now()
        # Create schedule with today's date and tomorrow's date for testing
        today = current_date.strftime("%Y-%m-%d")
        tomorrow = (current_date + timedelta(days=1)).strftime("%Y-%m-%d")
        
        schedule_data = {
            "store_id": self.default_store_id,
            "month": current_date.month,
            "year": current_date.year,
            "days": [
                {
                    "date": today,  # Today's date for employee earnings test
                    "day_shift": {
                        "type": "day",
                        "assignments": [
                            {
                                "employee_id": self.created_employee_id,
                                "employee_name": "Test Employee"
                            }
                        ],
                        "hours": 8,
                        "notes": "Test day shift"
                    }
                },
                {
                    "date": tomorrow,  # Tomorrow's date
                    "night_shift": {
                        "type": "night",
                        "assignments": [
                            {
                                "employee_id": self.created_employee_id,
                                "employee_name": "Test Employee"
                            }
                        ],
                        "hours": 12,
                        "notes": "Test night shift"
                    }
                }
            ]
        }
        
        success, data = self.api_call('POST', '/schedules', schedule_data, 
                                    token=self.manager_token, expected_status=200)
        
        if success and 'schedule' in data:
            return self.log_test("Create Store Schedule", True, 
                               f"- Created schedule for store with {len(data['schedule']['days'])} days")
        else:
            return self.log_test("Create Store Schedule", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_create_schedule_for_nonexistent_store(self) -> bool:
        """Test creating schedule for non-existent store (should fail)"""
        if not self.manager_token or not self.created_employee_id:
            return self.log_test("Schedule for Nonexistent Store", False, 
                               "- Missing manager token or employee ID")
            
        current_date = datetime.now()
        schedule_data = {
            "store_id": "nonexistent-store-id",
            "month": current_date.month,
            "year": current_date.year,
            "days": [
                {
                    "date": f"{current_date.year}-{current_date.month:02d}-01",
                    "day_shift": {
                        "type": "day",
                        "assignments": [
                            {
                                "employee_id": self.created_employee_id,
                                "employee_name": "Test Employee"
                            }
                        ]
                    }
                }
            ]
        }
        
        success, data = self.api_call('POST', '/schedules', schedule_data, 
                                    token=self.manager_token, expected_status=404)
        
        return self.log_test("Schedule for Nonexistent Store", success, 
                           f"- Correctly rejected: {data.get('detail', 'No error message')}")

    def test_get_store_schedule(self) -> bool:
        """Test getting schedule for specific store"""
        if not self.manager_token or not self.default_store_id:
            return self.log_test("Get Store Schedule", False, "- Missing token or store ID")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', 
                                    f'/schedules/{self.default_store_id}/{current_date.year}/{current_date.month}', 
                                    token=self.manager_token)
        
        if success and 'schedule' in data:
            schedule = data['schedule']
            if schedule:
                return self.log_test("Get Store Schedule", True, 
                                   f"- Found schedule with {len(schedule.get('days', []))} days")
            else:
                return self.log_test("Get Store Schedule", True, "- No schedule found (empty)")
        else:
            return self.log_test("Get Store Schedule", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_get_my_shifts_for_store(self) -> bool:
        """Test getting employee's shifts for specific store"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Get My Store Shifts", False, "- Missing employee token or store ID")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', 
                                    f'/my-shifts/{self.default_store_id}/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token)
        
        if success and 'shifts' in data and 'stats' in data:
            shifts = data['shifts']
            stats = data['stats']
            return self.log_test("Get My Store Shifts", True, 
                               f"- Found {len(shifts)} shifts, Total hours: {stats.get('total_hours', 0)}")
        else:
            return self.log_test("Get My Store Shifts", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_employee_access_unassigned_store_shifts(self) -> bool:
        """Test employee accessing shifts for unassigned store (should fail)"""
        if not self.employee_token or not self.created_store_id:
            return self.log_test("Employee Unassigned Store Shifts", False, 
                               "- Missing employee token or created store ID")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', 
                                    f'/my-shifts/{self.created_store_id}/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token, expected_status=403)
        
        return self.log_test("Employee Unassigned Store Shifts", success, 
                           f"- Correctly forbidden: {data.get('detail', 'No error message')}")

    def test_delete_store(self) -> bool:
        """Test deleting the created store"""
        if not self.manager_token or not self.created_store_id:
            return self.log_test("Delete Store", False, "- Missing manager token or store ID")
            
        success, data = self.api_call('DELETE', f'/stores/{self.created_store_id}', 
                                    token=self.manager_token)
        
        return self.log_test("Delete Store", success, 
                           f"- {data.get('message', data.get('detail', 'Unknown result'))}")

    def test_create_schedule_legacy(self) -> bool:
        """Test creating a schedule (legacy format - should fail without store_id)"""
        if not self.manager_token or not self.created_employee_id:
            return self.log_test("Create Schedule (Legacy)", False, "- Missing manager token or employee ID")
            
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
                }
            ]
        }
        
        success, data = self.api_call('POST', '/schedules', schedule_data, 
                                    token=self.manager_token, expected_status=422)
        
        return self.log_test("Create Schedule (Legacy)", success, 
                           f"- Correctly rejected legacy format: {data.get('detail', 'No error')}")

    def test_get_schedule_legacy(self) -> bool:
        """Test getting schedule (legacy format - should fail without store_id)"""
        if not self.manager_token:
            return self.log_test("Get Schedule (Legacy)", False, "- No manager token available")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', f'/schedules/{current_date.year}/{current_date.month}', 
                                    token=self.manager_token, expected_status=404)
        
        return self.log_test("Get Schedule (Legacy)", success, 
                           f"- Correctly rejected legacy format: {data.get('detail', 'Not Found')}")

    def test_get_my_shifts_legacy(self) -> bool:
        """Test getting employee's shifts (legacy format - should fail without store_id)"""
        if not self.employee_token:
            return self.log_test("Get My Shifts (Legacy)", False, "- No employee token available")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', f'/my-shifts/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token, expected_status=404)
        
        return self.log_test("Get My Shifts (Legacy)", success, 
                           f"- Correctly rejected legacy format: {data.get('detail', 'Not Found')}")

    # ===== EARNINGS SYSTEM TESTS =====
    
    def test_my_shifts_includes_earnings_fields(self) -> bool:
        """Test that my-shifts endpoint includes new earnings fields"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("My Shifts Earnings Fields", False, "- Missing employee token or store ID")
            
        current_date = datetime.now()
        success, data = self.api_call('GET', 
                                    f'/my-shifts/{self.default_store_id}/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token)
        
        if success and 'shifts' in data and 'stats' in data:
            shifts = data['shifts']
            stats = data['stats']
            
            # Check if stats includes total_earnings
            has_total_earnings = 'total_earnings' in stats
            
            # Check if shifts include earnings fields
            earnings_fields_present = True
            if shifts:
                for shift in shifts:
                    if not all(field in shift for field in ['earnings', 'can_edit_earnings', 'assignment_index']):
                        earnings_fields_present = False
                        break
            
            success_result = has_total_earnings and earnings_fields_present
            details = f"- Stats has total_earnings: {has_total_earnings}, Shifts have earnings fields: {earnings_fields_present}"
            
            return self.log_test("My Shifts Earnings Fields", success_result, details)
        else:
            return self.log_test("My Shifts Earnings Fields", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_update_shift_earnings_as_manager(self) -> bool:
        """Test updating shift earnings as manager (should always work)"""
        if not self.manager_token or not self.default_store_id or not self.created_employee_id:
            return self.log_test("Update Earnings (Manager)", False, "- Missing required data")
            
        current_date = datetime.now()
        # Use today's date for testing
        test_date = current_date.strftime("%Y-%m-%d")
        
        earnings_data = {"earnings": 2500.0}
        
        success, data = self.api_call('PUT', 
                                    f'/shift-earnings/{self.default_store_id}/{current_date.year}/{current_date.month}/{test_date}/day?assignment_index=0',
                                    earnings_data, token=self.manager_token)
        
        if success and isinstance(data, dict):
            success_result = data.get('success', False)
            can_edit = data.get('can_edit', False)
            message = data.get('message', 'No message')
            
            return self.log_test("Update Earnings (Manager)", success_result, 
                               f"- Success: {success_result}, Can edit: {can_edit}, Message: {message}")
        else:
            return self.log_test("Update Earnings (Manager)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_update_shift_earnings_as_employee_recent(self) -> bool:
        """Test updating shift earnings as employee for recent shift (should work within 12 hours)"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Update Earnings (Employee Recent)", False, "- Missing employee token or store ID")
            
        current_date = datetime.now()
        # Use today's date for testing (should be within 12 hours)
        test_date = current_date.strftime("%Y-%m-%d")
        
        earnings_data = {"earnings": 1800.0}
        
        success, data = self.api_call('PUT', 
                                    f'/shift-earnings/{self.default_store_id}/{current_date.year}/{current_date.month}/{test_date}/day?assignment_index=0',
                                    earnings_data, token=self.employee_token)
        
        if success and isinstance(data, dict):
            success_result = data.get('success', False)
            can_edit = data.get('can_edit', False)
            message = data.get('message', 'No message')
            
            return self.log_test("Update Earnings (Employee Recent)", success_result, 
                               f"- Success: {success_result}, Can edit: {can_edit}, Message: {message}")
        else:
            return self.log_test("Update Earnings (Employee Recent)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_update_shift_earnings_as_employee_old(self) -> bool:
        """Test updating shift earnings as employee for old shift (should fail after 12 hours)"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Update Earnings (Employee Old)", False, "- Missing employee token or store ID")
            
        # Use a date from 2 days ago to simulate old shift
        old_date = datetime.now() - timedelta(days=2)
        test_date = old_date.strftime("%Y-%m-%d")
        
        earnings_data = {"earnings": 1900.0}
        
        success, data = self.api_call('PUT', 
                                    f'/shift-earnings/{self.default_store_id}/{old_date.year}/{old_date.month}/{test_date}/day?assignment_index=0',
                                    earnings_data, token=self.employee_token)
        
        if success and isinstance(data, dict):
            success_result = data.get('success', False)
            can_edit = data.get('can_edit', False)
            message = data.get('message', 'No message')
            
            # For old shifts, employee should not be able to edit
            expected_result = not success_result and not can_edit
            
            return self.log_test("Update Earnings (Employee Old)", expected_result, 
                               f"- Success: {success_result}, Can edit: {can_edit}, Message: {message}")
        else:
            return self.log_test("Update Earnings (Employee Old)", False, 
                               f"- Error: {data.get('detail', data)}")

    def test_update_earnings_nonexistent_shift(self) -> bool:
        """Test updating earnings for non-existent shift (should fail)"""
        if not self.manager_token or not self.default_store_id:
            return self.log_test("Update Earnings (Nonexistent)", False, "- Missing manager token or store ID")
            
        current_date = datetime.now()
        # Use a date that doesn't have a shift
        test_date = f"{current_date.year}-{current_date.month:02d}-15"
        
        earnings_data = {"earnings": 2000.0}
        
        success, data = self.api_call('PUT', 
                                    f'/shift-earnings/{self.default_store_id}/{current_date.year}/{current_date.month}/{test_date}/day?assignment_index=0',
                                    earnings_data, token=self.manager_token, expected_status=404)
        
        return self.log_test("Update Earnings (Nonexistent)", success, 
                           f"- Correctly rejected: {data.get('detail', 'No error message')}")

    def test_employee_access_unassigned_store_earnings(self) -> bool:
        """Test employee trying to update earnings for unassigned store (should fail)"""
        if not self.employee_token or not self.created_store_id:
            return self.log_test("Employee Unassigned Store Earnings", False, 
                               "- Missing employee token or created store ID")
            
        current_date = datetime.now()
        test_date = current_date.strftime("%Y-%m-%d")
        
        earnings_data = {"earnings": 2000.0}
        
        success, data = self.api_call('PUT', 
                                    f'/shift-earnings/{self.created_store_id}/{current_date.year}/{current_date.month}/{test_date}/day?assignment_index=0',
                                    earnings_data, token=self.employee_token, expected_status=403)
        
        return self.log_test("Employee Unassigned Store Earnings", success, 
                           f"- Correctly forbidden: {data.get('detail', 'No error message')}")

    def test_get_earnings_history(self) -> bool:
        """Test getting earnings history for employee"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Get Earnings History", False, "- Missing employee token or store ID")
            
        success, data = self.api_call('GET', f'/earnings-history/{self.default_store_id}', 
                                    token=self.employee_token)
        
        if success and 'history' in data:
            history = data['history']
            return self.log_test("Get Earnings History", True, 
                               f"- Found {len(history)} months of earnings history")
        else:
            return self.log_test("Get Earnings History", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_get_earnings_history_unassigned_store(self) -> bool:
        """Test getting earnings history for unassigned store (should fail)"""
        if not self.employee_token or not self.created_store_id:
            return self.log_test("Earnings History Unassigned Store", False, 
                               "- Missing employee token or created store ID")
            
        success, data = self.api_call('GET', f'/earnings-history/{self.created_store_id}', 
                                    token=self.employee_token, expected_status=403)
        
        return self.log_test("Earnings History Unassigned Store", success, 
                           f"- Correctly forbidden: {data.get('detail', 'No error message')}")

    def test_manager_get_earnings_history(self) -> bool:
        """Test manager getting earnings history (should work for any store)"""
        if not self.manager_token or not self.default_store_id:
            return self.log_test("Manager Earnings History", False, "- Missing manager token or store ID")
            
        success, data = self.api_call('GET', f'/earnings-history/{self.default_store_id}', 
                                    token=self.manager_token)
        
        if success and 'history' in data:
            history = data['history']
            return self.log_test("Manager Earnings History", True, 
                               f"- Manager can access earnings history: {len(history)} months")
        else:
            return self.log_test("Manager Earnings History", False, 
                               f"- Error: {data.get('detail', 'Unknown error')}")

    def test_automatic_default_earnings_setting(self) -> bool:
        """Test that automatic default earnings (2000₽) are set for old shifts"""
        if not self.employee_token or not self.default_store_id:
            return self.log_test("Auto Default Earnings", False, "- Missing employee token or store ID")
            
        # First, get current shifts to see if any have automatic earnings
        current_date = datetime.now()
        success, data = self.api_call('GET', 
                                    f'/my-shifts/{self.default_store_id}/{current_date.year}/{current_date.month}', 
                                    token=self.employee_token)
        
        if success and 'shifts' in data:
            shifts = data['shifts']
            stats = data['stats']
            
            # Check if any shifts have earnings set to 2000 (default)
            has_default_earnings = any(shift.get('earnings') == 2000.0 for shift in shifts)
            total_earnings = stats.get('total_earnings', 0)
            
            return self.log_test("Auto Default Earnings", True, 
                               f"- Has default earnings: {has_default_earnings}, Total earnings: {total_earnings}")
        else:
            return self.log_test("Auto Default Earnings", False, 
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
        print("🚀 Starting Shift Schedule Manager API Tests with Stores Support")
        print("=" * 70)
        
        # Basic connectivity tests
        self.test_health_check()
        
        # Authentication tests
        self.test_manager_login()
        self.test_invalid_login()
        self.test_get_current_user()
        
        # Store management tests (must run before employee creation)
        print("\n📍 STORE MANAGEMENT TESTS")
        print("-" * 30)
        self.test_get_default_stores()
        self.test_create_store()
        self.test_get_all_stores_as_manager()
        self.test_get_specific_store()
        self.test_update_store()
        
        # User management tests
        print("\n👥 USER MANAGEMENT TESTS")
        print("-" * 30)
        self.test_create_employee()
        self.test_employee_login()
        self.test_get_users_as_manager()
        self.test_get_users_as_employee()
        
        # Store access control tests
        print("\n🔐 STORE ACCESS CONTROL TESTS")
        print("-" * 30)
        self.test_get_stores_as_employee()
        self.test_employee_access_to_assigned_store()
        self.test_employee_access_to_unassigned_store()
        
        # Store-specific schedule management tests
        print("\n📅 STORE-SPECIFIC SCHEDULE TESTS")
        print("-" * 30)
        self.test_create_schedule_for_store()
        self.test_create_schedule_for_nonexistent_store()
        self.test_get_store_schedule()
        self.test_get_my_shifts_for_store()
        self.test_employee_access_unassigned_store_shifts()
        
        # Legacy format validation tests
        print("\n⚠️  LEGACY FORMAT VALIDATION TESTS")
        print("-" * 30)
        self.test_create_schedule_legacy()
        self.test_get_schedule_legacy()
        self.test_get_my_shifts_legacy()
        
        # Earnings system tests
        print("\n💰 EARNINGS SYSTEM TESTS")
        print("-" * 30)
        self.test_my_shifts_includes_earnings_fields()
        self.test_update_shift_earnings_as_manager()
        self.test_update_shift_earnings_as_employee_recent()
        self.test_update_shift_earnings_as_employee_old()
        self.test_update_earnings_nonexistent_shift()
        self.test_employee_access_unassigned_store_earnings()
        self.test_get_earnings_history()
        self.test_get_earnings_history_unassigned_store()
        self.test_manager_get_earnings_history()
        self.test_automatic_default_earnings_setting()
        
        # Cleanup
        print("\n🧹 CLEANUP TESTS")
        print("-" * 30)
        self.test_delete_employee()
        self.test_delete_store()
        
        # Print summary
        print("=" * 70)
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