"""
Phase 1 Implementation Test Suite
Tests all core Phase 1 backend foundation components
"""
import requests
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8000"
API_V1 = "/api/v1"

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}


def print_header(text: str):
    """Print section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")


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


def test_root_endpoint():
    """Test 1: Root endpoint"""
    print_header("TEST 1: Root Endpoint")

    try:
        response = requests.get(f"{BASE_URL}/")

        # Check status code
        print_test("Status Code 200", response.status_code == 200,
                   f"Got: {response.status_code}")

        data = response.json()

        # Check response format
        print_test("Has 'success' field", "success" in data,
                   f"Response: {json.dumps(data, indent=2)}")
        print_test("success = True", data.get("success") == True)
        print_test("Has 'message' field", "message" in data)
        print_test("Has 'data' field", "data" in data)

        # Check data content
        if "data" in data:
            print_test("data.name = 'TRANSLATRIX PRO'",
                      data["data"].get("name") == "TRANSLATRIX PRO")
            print_test("data.version present", "version" in data["data"])
            print_test("data.environment present", "environment" in data["data"])

    except Exception as e:
        print_test("Root endpoint request", False, f"Error: {str(e)}")


def test_health_check():
    """Test 2: Health check endpoint"""
    print_header("TEST 2: Health Check Endpoint")

    try:
        response = requests.get(f"{BASE_URL}/health")

        print_test("Status Code 200", response.status_code == 200)

        data = response.json()
        print_test("Has 'success' field", "success" in data)
        print_test("success = True", data.get("success") == True)
        print_test("Has 'data' field", "data" in data)

        if "data" in data:
            print_test("data.status = 'healthy'",
                      data["data"].get("status") == "healthy")
            print_test("data.app_name present", "app_name" in data["data"])
            print_test("data.environment present", "environment" in data["data"])

    except Exception as e:
        print_test("Health check request", False, f"Error: {str(e)}")


def test_readiness_probe():
    """Test 3: Readiness probe"""
    print_header("TEST 3: Readiness Probe")

    try:
        response = requests.get(f"{BASE_URL}/ready")

        print_test("Status Code 200 or 503",
                   response.status_code in [200, 503],
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Has 'success' field", "success" in data)
        print_test("Has 'data' field", "data" in data)

        if "data" in data:
            print_test("data.ready field present", "ready" in data["data"])
            print_test("data.dependencies present", "dependencies" in data["data"])

    except Exception as e:
        print_test("Readiness probe request", False, f"Error: {str(e)}")


def test_request_id_middleware():
    """Test 4: Request ID middleware"""
    print_header("TEST 4: Request ID Middleware")

    try:
        # Test 1: Server generates request ID
        response = requests.get(f"{BASE_URL}/health")
        print_test("Response has X-Request-ID header",
                   "X-Request-ID" in response.headers,
                   f"Headers: {dict(response.headers)}")

        # Test 2: Server accepts custom request ID
        custom_id = "test-request-123"
        response = requests.get(f"{BASE_URL}/health",
                               headers={"X-Request-ID": custom_id})
        print_test("Server returns custom X-Request-ID",
                   response.headers.get("X-Request-ID") == custom_id,
                   f"Expected: {custom_id}, Got: {response.headers.get('X-Request-ID')}")

    except Exception as e:
        print_test("Request ID middleware test", False, f"Error: {str(e)}")


def test_cors_middleware():
    """Test 5: CORS middleware"""
    print_header("TEST 5: CORS Middleware")

    try:
        response = requests.options(f"{BASE_URL}/health",
                                   headers={"Origin": "http://localhost:3000"})

        print_test("CORS headers present",
                   "access-control-allow-origin" in response.headers,
                   f"Headers: {dict(response.headers)}")

        print_test("X-Request-ID in exposed headers",
                   "X-Request-ID" in response.headers.get("access-control-expose-headers", ""),
                   f"Exposed headers: {response.headers.get('access-control-expose-headers')}")

    except Exception as e:
        print_test("CORS middleware test", False, f"Error: {str(e)}")


def test_standard_response_format():
    """Test 6: Standard response format"""
    print_header("TEST 6: Standard Response Format")

    try:
        response = requests.get(f"{BASE_URL}/health")
        data = response.json()

        # Test response structure
        print_test("Response is JSON", True)
        print_test("Has 'success' boolean field",
                   isinstance(data.get("success"), bool))
        print_test("Has 'message' string field",
                   isinstance(data.get("message"), str))
        print_test("Has 'data' field", "data" in data)

        # Meta field is optional
        if "meta" in data:
            print_test("meta is dict", isinstance(data["meta"], dict))

    except Exception as e:
        print_test("Response format test", False, f"Error: {str(e)}")


def test_404_error_handling():
    """Test 7: 404 error handling"""
    print_header("TEST 7: 404 Error Handling")

    try:
        response = requests.get(f"{BASE_URL}/nonexistent-endpoint")

        print_test("Status Code 404", response.status_code == 404,
                   f"Got: {response.status_code}")

        data = response.json()
        print_test("Response is JSON", True)
        print_test("Has 'detail' or error info", "detail" in data or "message" in data)

    except Exception as e:
        print_test("404 error handling test", False, f"Error: {str(e)}")


def test_api_documentation():
    """Test 8: API documentation availability"""
    print_header("TEST 8: API Documentation (Debug Mode)")

    try:
        # In debug mode, docs should be available
        response = requests.get(f"{BASE_URL}/docs")

        print_test("Swagger UI accessible",
                   response.status_code == 200,
                   f"Status: {response.status_code}")

        print_test("Returns HTML",
                   "text/html" in response.headers.get("content-type", ""))

    except Exception as e:
        print_test("API docs test", False, f"Error: {str(e)}")


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
        print(f"{GREEN}{'='*60}{RESET}")
        print(f"{GREEN}{'ALL PHASE 1 TESTS PASSED!'.center(60)}{RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")
    else:
        print(f"{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}{'SOME TESTS FAILED'.center(60)}{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}\n")

        print(f"{YELLOW}Failed Tests:{RESET}")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  - {test['name']}")
                if test["details"]:
                    print(f"    {test['details']}")


if __name__ == "__main__":
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'TRANSLATRIX PRO - Phase 1 Implementation Test'.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"\nTesting backend at: {BASE_URL}\n")

    # Run all tests
    test_root_endpoint()
    test_health_check()
    test_readiness_probe()
    test_request_id_middleware()
    test_cors_middleware()
    test_standard_response_format()
    test_404_error_handling()
    test_api_documentation()

    # Print summary
    print_summary()
