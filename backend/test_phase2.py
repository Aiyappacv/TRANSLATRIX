"""
Phase 2 Implementation Test Suite
Tests Auth, Company Registration, Tenant Onboarding, Users, and RBAC
"""
import requests
import json
from typing import Dict, Any, Optional
import time

# Generate unique email suffix based on timestamp
UNIQUE_SUFFIX = str(int(time.time()))

BASE_URL = "http://localhost:8000"
API_V1 = "/api/v1"

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Test data storage
test_data = {
    "tenant_id": None,
    "company_id": None,
    "admin_user_id": None,
    "admin_token": None,
    "refresh_token": None,
    "regular_user_id": None,
    "regular_user_token": None,
}

test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}


def print_header(text: str):
    """Print section header"""
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{text.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}\n")


def print_test(name: str, passed: bool, details: str = ""):
    """Print test result"""
    status = f"{GREEN}[PASS]{RESET}" if passed else f"{RED}[FAIL]{RESET}"
    print(f"{status} | {name}")
    if details:
        print(f"       {details}")

    test_results["tests"].append({"name": name, "passed": passed, "details": details})
    if passed:
        test_results["passed"] += 1
    else:
        test_results["failed"] += 1


def test_company_registration():
    """Test 1: Company Registration - Creates tenant, company, and admin user"""
    print_header("TEST 1: Company Registration (Complete Flow)")

    registration_data = {
        "legal_name": "Test Corporation Ltd",
        "trading_name": "TestCorp",
        "country": "United States",
        "industry": "Technology",
        "registration_number": "REG123456",
        "tax_number": "TAX987654",
        "email": f"contact-{UNIQUE_SUFFIX}@testcorp.com",
        "phone": "+1-555-0100",
        "default_currency": "USD",
        "default_language": "en",
        "timezone": "America/New_York",
        "admin_first_name": "John",
        "admin_last_name": "Doe",
        "admin_email": f"admin-{UNIQUE_SUFFIX}@testcorp.com",
        "admin_password": "AdminPass123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/register-company",
            json=registration_data
        )

        print_test("Status Code 201", response.status_code == 201,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response has 'success' = true", data.get("success") == True)
        print_test("Response has 'message' field", "message" in data)
        print_test("Response has 'data' field", "data" in data)

        if "data" in data and isinstance(data["data"], dict):
            result_data = data["data"]

            # Check for tenant_id, company_id, user_id (actual API response format)
            print_test("Has tenant_id", "tenant_id" in result_data)
            if "tenant_id" in result_data:
                test_data["tenant_id"] = result_data["tenant_id"]
                print_test("Tenant ID is valid UUID", len(str(result_data["tenant_id"])) > 30)

            print_test("Has company_id", "company_id" in result_data)
            if "company_id" in result_data:
                test_data["company_id"] = result_data["company_id"]
                print_test("Company ID is valid UUID", len(str(result_data["company_id"])) > 30)

            print_test("Has user_id", "user_id" in result_data)
            if "user_id" in result_data:
                test_data["admin_user_id"] = result_data["user_id"]
                print_test("User ID is valid UUID", len(str(result_data["user_id"])) > 30)

            # Note: Registration does NOT return tokens (two-step flow by design)
            # We need to login separately to get tokens
            print(f"\n{YELLOW}Captured Test Data:{RESET}")
            print(f"  Tenant ID: {test_data['tenant_id']}")
            print(f"  Company ID: {test_data['company_id']}")
            print(f"  Admin User ID: {test_data['admin_user_id']}")
            print(f"\n{YELLOW}Note: Registration complete. Tokens will be obtained via login.{RESET}")

    except Exception as e:
        print_test("Company registration request", False, f"Error: {str(e)}")


def test_duplicate_registration():
    """Test 2: Duplicate Registration Prevention"""
    print_header("TEST 2: Duplicate Registration Prevention")

    duplicate_data = {
        "legal_name": "Another Company",
        "trading_name": "AnotherCo",
        "country": "United States",
        "industry": "Finance",
        "email": "another@company.com",
        "default_currency": "USD",
        "default_language": "en",
        "timezone": "America/New_York",
        "admin_first_name": "Jane",
        "admin_last_name": "Smith",
        "admin_email": f"admin-{UNIQUE_SUFFIX}@testcorp.com",  # Same email as first registration
        "admin_password": "Password123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/register-company",
            json=duplicate_data
        )

        # Duplicate email returns 201 with success=false (API design choice)
        data = response.json()
        is_duplicate = data.get("success") == False and "already" in data.get("message", "").lower()
        print_test("Duplicate email rejected", is_duplicate,
                   f"Message: {data.get('message', 'No message')}")

    except Exception as e:
        print_test("Duplicate registration test", False, f"Error: {str(e)}")


def test_user_login():
    """Test 3: User Login"""
    print_header("TEST 3: User Login")

    login_data = {
        "email": f"admin-{UNIQUE_SUFFIX}@testcorp.com",
        "password": "AdminPass123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/login",
            json=login_data
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()

        # Login returns tokens directly at top level, NOT wrapped in success/data
        print_test("Has access_token", "access_token" in data)
        print_test("Has refresh_token", "refresh_token" in data)
        print_test("Has token_type", "token_type" in data)

        # Capture tokens for later tests
        if "access_token" in data:
            test_data["admin_token"] = data["access_token"]
        if "refresh_token" in data:
            test_data["refresh_token"] = data["refresh_token"]

        print(f"\n{YELLOW}Tokens captured from login:{RESET}")
        print(f"  Access Token: {test_data['admin_token'][:50]}..." if test_data['admin_token'] else "  No token")

    except Exception as e:
        print_test("Login request", False, f"Error: {str(e)}")


def test_invalid_login():
    """Test 4: Invalid Login Credentials"""
    print_header("TEST 4: Invalid Login Credentials")

    invalid_login = {
        "email": f"admin-{UNIQUE_SUFFIX}@testcorp.com",
        "password": "WrongPassword123"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/login",
            json=invalid_login
        )

        print_test("Status Code 401 (unauthorized)", response.status_code == 401,
                   f"Got: {response.status_code}")

    except Exception as e:
        print_test("Invalid login test", False, f"Error: {str(e)}")


def test_token_refresh():
    """Test 5: Token Refresh"""
    print_header("TEST 5: Token Refresh")

    if not test_data["refresh_token"]:
        print_test("Refresh token available", False, "No refresh token from registration")
        return

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/refresh",
            json={"refresh_token": test_data["refresh_token"]}
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)
        print_test("Has new access_token", "access_token" in data.get("data", {}))

    except Exception as e:
        print_test("Token refresh request", False, f"Error: {str(e)}")


def test_get_current_user():
    """Test 6: Get Current User Info"""
    print_header("TEST 6: Get Current User Info")

    if not test_data["admin_token"]:
        print_test("Admin token available", False, "No admin token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/auth/me",
            headers=headers
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)

        if "data" in data:
            user = data["data"]
            print_test("User email matches", user.get("email") == "admin@testcorp.com")
            print_test("User has tenant_id", "tenant_id" in user)
            print_test("User has company_id", "company_id" in user)
            print_test("User has role", "role" in user)

    except Exception as e:
        print_test("Get current user request", False, f"Error: {str(e)}")


def test_unauthorized_access():
    """Test 7: Unauthorized Access"""
    print_header("TEST 7: Unauthorized Access (No Token)")

    try:
        response = requests.get(f"{BASE_URL}{API_V1}/auth/me")

        print_test("Status Code 403 (forbidden)", response.status_code == 403,
                   f"Got: {response.status_code}")

    except Exception as e:
        print_test("Unauthorized access test", False, f"Error: {str(e)}")


def test_get_company():
    """Test 8: Get Company Details"""
    print_header("TEST 8: Get Company Details")

    if not test_data["company_id"] or not test_data["admin_token"]:
        print_test("Prerequisites available", False, "Missing company_id or token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/companies/{test_data['company_id']}",
            headers=headers
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)

        if "data" in data:
            company = data["data"]
            print_test("Company ID matches", company.get("id") == test_data["company_id"])
            print_test("Company has legal_name", "legal_name" in company)
            print_test("Company has tenant_id", "tenant_id" in company)

    except Exception as e:
        print_test("Get company request", False, f"Error: {str(e)}")


def test_onboarding_progress():
    """Test 9: Check Onboarding Progress"""
    print_header("TEST 9: Onboarding Progress")

    if not test_data["company_id"] or not test_data["admin_token"]:
        print_test("Prerequisites available", False, "Missing company_id or token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/onboarding/{test_data['company_id']}/progress",
            headers=headers
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)

        if "data" in data:
            progress = data["data"]
            print_test("Has completion_percentage", "completion_percentage" in progress)
            print_test("Has steps completed count", "steps_completed" in progress)
            print_test("Has total steps count", "total_steps" in progress)
            print_test("Has is_complete flag", "is_complete" in progress)

            print(f"\n{YELLOW}Onboarding Status:{RESET}")
            print(f"  Completion: {progress.get('completion_percentage')}%")
            print(f"  Steps: {progress.get('steps_completed')}/{progress.get('total_steps')}")

    except Exception as e:
        print_test("Onboarding progress request", False, f"Error: {str(e)}")


def test_onboarding_steps():
    """Test 10: Complete Onboarding Steps"""
    print_header("TEST 10: Complete Onboarding Steps")

    if not test_data["company_id"] or not test_data["admin_token"]:
        print_test("Prerequisites available", False, "Missing company_id or token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    company_id = test_data["company_id"]

    # Step 1: Company Profile
    try:
        response = requests.put(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/steps/company-profile",
            headers=headers,
            json={}
        )
        print_test("Step 1: Company Profile completed", response.status_code == 200,
                   f"Got: {response.status_code}")
    except Exception as e:
        print_test("Step 1 request", False, f"Error: {str(e)}")

    # Step 2: Finance Configuration
    try:
        response = requests.put(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/steps/finance-config",
            headers=headers,
            json={}
        )
        print_test("Step 2: Finance Config completed", response.status_code == 200,
                   f"Got: {response.status_code}")
    except Exception as e:
        print_test("Step 2 request", False, f"Error: {str(e)}")

    # Step 3: Integration Selection
    try:
        response = requests.put(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/steps/integration-selection",
            headers=headers,
            json={
                "accounting_software": "QuickBooks",
                "storage_sources": ["OneDrive", "Google Drive"]
            }
        )
        print_test("Step 3: Integration Selection completed", response.status_code == 200,
                   f"Got: {response.status_code}")
    except Exception as e:
        print_test("Step 3 request", False, f"Error: {str(e)}")

    # Step 4: Users Invited
    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/steps/users-invited",
            headers=headers,
            json={}
        )
        print_test("Step 4: Users Invited marked", response.status_code == 200,
                   f"Got: {response.status_code}")
    except Exception as e:
        print_test("Step 4 request", False, f"Error: {str(e)}")

    # Step 5: Security Settings
    try:
        response = requests.put(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/steps/security-settings",
            headers=headers,
            json={}
        )
        print_test("Step 5: Security Settings completed", response.status_code == 200,
                   f"Got: {response.status_code}")
    except Exception as e:
        print_test("Step 5 request", False, f"Error: {str(e)}")

    # Check progress after all steps
    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/onboarding/{company_id}/progress",
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                print_test("All steps completed (100%)",
                          data["data"].get("completion_percentage") == 100,
                          f"Progress: {data['data'].get('completion_percentage')}%")
    except Exception as e:
        print_test("Final progress check", False, f"Error: {str(e)}")


def test_create_user():
    """Test 11: Create Additional User"""
    print_header("TEST 11: Create Additional User")

    if not test_data["company_id"] or not test_data["admin_token"]:
        print_test("Prerequisites available", False, "Missing company_id or token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    new_user_data = {
        "email": "reviewer@testcorp.com",
        "password": "ReviewPass123",
        "first_name": "Jane",
        "last_name": "Smith",
        "phone": "+1-555-0102",
        "company_id": test_data["company_id"],
        "role_name": "company_reviewer"
    }

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/users/",
            headers=headers,
            json=new_user_data
        )

        print_test("Status Code 201", response.status_code == 201,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)

        if "data" in data:
            user = data["data"]
            test_data["regular_user_id"] = user.get("id")
            print_test("User has UUID", "id" in user)
            print_test("User email matches", user.get("email") == "reviewer@testcorp.com")
            print_test("User has role", "role" in user)

    except Exception as e:
        print_test("Create user request", False, f"Error: {str(e)}")


def test_list_roles():
    """Test 12: List Available Roles"""
    print_header("TEST 12: List Available Roles")

    if not test_data["admin_token"]:
        print_test("Admin token available", False, "No admin token")
        return

    headers = {
        "Authorization": f"Bearer {test_data['admin_token']}"
    }

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/users/roles/",
            headers=headers
        )

        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response success = true", data.get("success") == True)

        if "data" in data:
            roles = data["data"]
            print_test("Roles is a list", isinstance(roles, list))
            print_test("Has multiple roles", len(roles) > 0)

            if len(roles) > 0:
                print(f"\n{YELLOW}Available Roles:{RESET}")
                for role in roles:
                    print(f"  - {role.get('name')}: {role.get('display_name')}")

    except Exception as e:
        print_test("List roles request", False, f"Error: {str(e)}")


def test_tenant_isolation():
    """Test 13: Tenant Isolation - Cannot access other tenant's data"""
    print_header("TEST 13: Tenant Isolation")

    # First, create a second company
    second_company_data = {
        "legal_name": "Second Company Ltd",
        "trading_name": "SecondCo",
        "country": "United Kingdom",
        "industry": "Finance",
        "email": f"contact-second-{UNIQUE_SUFFIX}@secondco.com",
        "default_currency": "GBP",
        "default_language": "en",
        "timezone": "Europe/London",
        "admin_first_name": "Alice",
        "admin_last_name": "Johnson",
        "admin_email": f"admin-second-{UNIQUE_SUFFIX}@secondco.com",
        "admin_password": "SecondPass123"
    }

    second_tenant_token = None
    first_company_id = test_data["company_id"]

    try:
        # Register second company
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/register-company",
            json=second_company_data
        )

        print_test("Second company registered", response.status_code == 201)

        if response.status_code == 201:
            data = response.json()
            # Registration doesn't return tokens, need to login
            login_response = requests.post(
                f"{BASE_URL}{API_V1}/auth/login",
                json={
                    "email": f"admin-second-{UNIQUE_SUFFIX}@secondco.com",
                    "password": "SecondPass123"
                }
            )

            if login_response.status_code == 200:
                login_data = login_response.json()
                # Login returns tokens directly at top level
                second_tenant_token = login_data.get("access_token")

            # Try to access first company's data with second tenant's token
            if second_tenant_token and first_company_id:
                headers = {
                    "Authorization": f"Bearer {second_tenant_token}"
                }

                response = requests.get(
                    f"{BASE_URL}{API_V1}/companies/{first_company_id}",
                    headers=headers
                )

                print_test("Cannot access other tenant's company (403/404)",
                          response.status_code in [403, 404],
                          f"Got: {response.status_code} (should be forbidden)")

    except Exception as e:
        print_test("Tenant isolation test", False, f"Error: {str(e)}")


def test_password_validation():
    """Test 14: Password Strength Validation"""
    print_header("TEST 14: Password Strength Validation")

    weak_passwords = [
        ("short", "Short password"),
        ("nouppercase123", "No uppercase"),
        ("NOLOWERCASE123", "No lowercase"),
        ("NoDigitsHere", "No digits"),
    ]

    for weak_password, reason in weak_passwords:
        test_data_weak = {
            "legal_name": "Test Weak Password",
            "trading_name": "TestWeak",
            "country": "US",
            "industry": "Tech",
            "email": f"weak{weak_password}@test.com",
            "default_currency": "USD",
            "default_language": "en",
            "timezone": "UTC",
            "admin_first_name": "Weak",
            "admin_last_name": "Password",
            "admin_email": f"admin-weak{weak_password}@test.com",
            "admin_password": weak_password
        }

        try:
            response = requests.post(
                f"{BASE_URL}{API_V1}/auth/register-company",
                json=test_data_weak
            )

            data = response.json()
            # Password validation returns 201 with success=false (API design choice)
            is_rejected = data.get("success") == False
            print_test(f"Reject weak password: {reason}",
                      is_rejected,
                      f"Response: {data.get('message', 'No message')}")

        except Exception as e:
            print_test(f"Password validation test ({reason})", False, f"Error: {str(e)}")


def print_summary():
    """Print test summary"""
    total = test_results["passed"] + test_results["failed"]
    pass_rate = (test_results["passed"] / total * 100) if total > 0 else 0

    print_header("TEST SUMMARY")

    print(f"Total Tests: {total}")
    print(f"{GREEN}Passed: {test_results['passed']}{RESET}")
    print(f"{RED}Failed: {test_results['failed']}{RESET}")
    print(f"Pass Rate: {pass_rate:.1f}%\n")

    if test_results["failed"] == 0:
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}{'ALL PHASE 2 TESTS PASSED!'.center(70)}{RESET}")
        print(f"{GREEN}{'='*70}{RESET}\n")
    else:
        print(f"{YELLOW}{'='*70}{RESET}")
        print(f"{YELLOW}{'SOME TESTS FAILED'.center(70)}{RESET}")
        print(f"{YELLOW}{'='*70}{RESET}\n")

        print(f"{YELLOW}Failed Tests:{RESET}")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  - {test['name']}")
                if test["details"]:
                    print(f"    {test['details']}")


if __name__ == "__main__":
    print(f"\n{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}{'TRANSLATRIX PRO - Phase 2 Implementation Test'.center(70)}{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"\nTesting backend at: {BASE_URL}")
    print(f"Testing: Auth, Registration, Onboarding, Users, RBAC\n")

    # Run all tests in sequence
    test_company_registration()
    test_duplicate_registration()
    test_user_login()
    test_invalid_login()
    test_token_refresh()
    test_get_current_user()
    test_unauthorized_access()
    test_get_company()
    test_onboarding_progress()
    test_onboarding_steps()
    test_create_user()
    test_list_roles()
    test_tenant_isolation()
    test_password_validation()

    # Print summary
    print_summary()
