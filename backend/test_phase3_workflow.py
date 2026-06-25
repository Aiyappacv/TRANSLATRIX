"""
Phase 3+ Workflow Test Suite
Tests the complete file processing workflow:
- File Upload (Phase 4)
- File Management (Phase 5)
- OCR Processing (Phase 6)
- Translation (Phase 7)
- Entry Extraction & Classification (Phase 8)
"""
import requests
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

BASE_URL = "http://localhost:8000"
API_V1 = "/api/v1"

# ANSI color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

# Test credentials (from Phase 2)
TEST_EMAIL = "admin-unique123@testcorp.com"
TEST_PASSWORD = "AdminPass123"

# Global state
access_token = None
tenant_id = None
company_id = None
uploaded_file_id = None
ocr_result_id = None
translation_id = None

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


def get_auth_headers() -> Dict[str, str]:
    """Get authorization headers"""
    return {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def login():
    """Login and get access token"""
    global access_token, tenant_id, company_id

    print_header("AUTHENTICATION")

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            }
        )

        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")

            # Decode token to get user info (or get from /auth/me)
            me_response = requests.get(
                f"{BASE_URL}{API_V1}/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )

            if me_response.status_code == 200:
                user_data = me_response.json()
                if "data" in user_data:
                    tenant_id = user_data["data"].get("tenant_id")
                    company_id = user_data["data"].get("company_id")

                print_test("Login successful", True,
                          f"Tenant: {tenant_id}, Company: {company_id}")
            else:
                print_test("Get user info", False, f"Status: {me_response.status_code}")
        else:
            print_test("Login", False, f"Status: {response.status_code}")
            return False

    except Exception as e:
        print_test("Login", False, f"Error: {str(e)}")
        return False

    return True


def create_test_file() -> Path:
    """Create a test invoice file"""
    test_file = Path("/tmp/test_invoice.txt")

    content = """
    INVOICE

    Invoice Number: INV-2024-001
    Date: 2024-01-15

    Bill To:
    Acme Corporation
    123 Main Street
    New York, NY 10001

    Items:
    - Office Supplies: $500.00
    - Software License: $1,200.00
    - Consulting Services: $3,000.00

    Subtotal: $4,700.00
    Tax (10%): $470.00
    Total: $5,170.00

    Payment Terms: Net 30
    """

    test_file.write_text(content)
    return test_file


def test_file_upload():
    """Test 1: Upload a file"""
    global uploaded_file_id

    print_header("TEST 1: File Upload")

    try:
        # Create test file
        test_file = create_test_file()

        # Upload file
        with open(test_file, 'rb') as f:
            files = {'file': ('test_invoice.txt', f, 'text/plain')}
            headers = {"Authorization": f"Bearer {access_token}"}

            response = requests.post(
                f"{BASE_URL}{API_V1}/files/upload",
                headers=headers,
                files=files
            )

        print_test("Status Code 201", response.status_code == 201,
                   f"Got: {response.status_code}")

        if response.status_code == 201:
            data = response.json()
            print_test("Response has 'success' field", "success" in data)

            if "data" in data:
                uploaded_file_id = data["data"].get("id")
                print_test("File uploaded successfully", uploaded_file_id is not None,
                          f"File ID: {uploaded_file_id}")
                print(f"       File name: {data['data'].get('original_filename')}")
                print(f"       Size: {data['data'].get('size')} bytes")
                print(f"       Status: {data['data'].get('status')}")
        else:
            print_test("File upload", False, f"Response: {response.text}")

    except Exception as e:
        print_test("File upload", False, f"Error: {str(e)}")


def test_list_files():
    """Test 2: List uploaded files"""
    print_header("TEST 2: List Files")

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/files",
            headers=get_auth_headers()
        )

        print_test("Status Code 200", response.status_code == 200)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                files = data["data"]
                print_test("Files list returned", isinstance(files, list))
                print_test("Files count > 0", len(files) > 0,
                          f"Found {len(files)} file(s)")

                if len(files) > 0:
                    print(f"       Latest file: {files[0].get('original_filename')}")
        else:
            print_test("List files", False, f"Status: {response.status_code}")

    except Exception as e:
        print_test("List files", False, f"Error: {str(e)}")


def test_get_file_details():
    """Test 3: Get file details"""
    print_header("TEST 3: Get File Details")

    if not uploaded_file_id:
        print_test("Get file details", False, "No file ID available")
        return

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/files/{uploaded_file_id}",
            headers=get_auth_headers()
        )

        print_test("Status Code 200", response.status_code == 200)

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                file_data = data["data"]
                print_test("File details returned", True)
                print(f"       Name: {file_data.get('original_filename')}")
                print(f"       Status: {file_data.get('status')}")
                print(f"       MIME type: {file_data.get('mime_type')}")
                print(f"       Storage path: {file_data.get('storage_path')}")
        else:
            print_test("Get file details", False, f"Status: {response.status_code}")

    except Exception as e:
        print_test("Get file details", False, f"Error: {str(e)}")


def test_ocr_processing():
    """Test 4: OCR Processing"""
    global ocr_result_id

    print_header("TEST 4: OCR Processing")

    if not uploaded_file_id:
        print_test("OCR processing", False, "No file ID available")
        return

    try:
        # Trigger OCR
        response = requests.post(
            f"{BASE_URL}{API_V1}/files/{uploaded_file_id}/ocr",
            headers=get_auth_headers(),
            json={
                "provider": "mistral",
                "language": "en"
            }
        )

        print_test("OCR request accepted", response.status_code in [200, 201, 202],
                   f"Got: {response.status_code}")

        if response.status_code in [200, 201, 202]:
            data = response.json()

            if "data" in data:
                ocr_data = data["data"]
                ocr_result_id = ocr_data.get("id")
                status = ocr_data.get("status")

                print_test("OCR result created", ocr_result_id is not None,
                          f"OCR ID: {ocr_result_id}")
                print(f"       Status: {status}")

                # Wait for OCR to complete (if processing)
                if status == "processing":
                    print(f"       Waiting for OCR to complete...")
                    time.sleep(5)

                    # Check status
                    status_response = requests.get(
                        f"{BASE_URL}{API_V1}/files/{uploaded_file_id}/ocr",
                        headers=get_auth_headers()
                    )

                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        if "data" in status_data:
                            final_status = status_data["data"].get("status")
                            print(f"       Final status: {final_status}")

                            if final_status == "completed":
                                print_test("OCR completed", True)
                                print(f"       Pages: {status_data['data'].get('total_pages')}")
                                print(f"       Confidence: {status_data['data'].get('average_confidence')}")
        else:
            print_test("OCR processing", False, f"Response: {response.text}")

    except Exception as e:
        print_test("OCR processing", False, f"Error: {str(e)}")


def test_translation():
    """Test 5: Translation"""
    global translation_id

    print_header("TEST 5: Translation")

    if not uploaded_file_id:
        print_test("Translation", False, "No file ID available")
        return

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/files/{uploaded_file_id}/translate",
            headers=get_auth_headers(),
            json={
                "source_language": "en",
                "target_language": "en",  # No translation needed for English
                "provider": "openai"
            }
        )

        print_test("Translation request", response.status_code in [200, 201, 202],
                   f"Got: {response.status_code}")

        if response.status_code in [200, 201, 202]:
            data = response.json()
            if "data" in data:
                translation_id = data["data"].get("id")
                print_test("Translation created", translation_id is not None,
                          f"Translation ID: {translation_id}")
        else:
            print_test("Translation", False, f"Response: {response.text}")

    except Exception as e:
        print_test("Translation", False, f"Error: {str(e)}")


def test_extraction():
    """Test 6: Financial Entry Extraction"""
    print_header("TEST 6: Financial Entry Extraction")

    if not uploaded_file_id:
        print_test("Extraction", False, "No file ID available")
        return

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/files/{uploaded_file_id}/extract",
            headers=get_auth_headers(),
            json={
                "extract_type": "financial_entries"
            }
        )

        print_test("Extraction request", response.status_code in [200, 201, 202],
                   f"Got: {response.status_code}")

        if response.status_code in [200, 201, 202]:
            data = response.json()
            if "data" in data:
                print_test("Extraction successful", True)
                print(f"       Extraction data available")
        else:
            print_test("Extraction", False, f"Response: {response.text}")

    except Exception as e:
        print_test("Extraction", False, f"Error: {str(e)}")


def test_create_entry():
    """Test 7: Create Financial Entry"""
    print_header("TEST 7: Create Financial Entry")

    try:
        response = requests.post(
            f"{BASE_URL}{API_V1}/entries",
            headers=get_auth_headers(),
            json={
                "file_id": uploaded_file_id,
                "entry_type": "expense",
                "amount": 5170.00,
                "currency": "USD",
                "description": "Office supplies and consulting",
                "vendor": "Acme Corporation",
                "invoice_number": "INV-2024-001",
                "invoice_date": "2024-01-15"
            }
        )

        print_test("Entry creation", response.status_code in [200, 201],
                   f"Got: {response.status_code}")

        if response.status_code in [200, 201]:
            data = response.json()
            if "data" in data:
                entry_id = data["data"].get("id")
                print_test("Entry created", entry_id is not None,
                          f"Entry ID: {entry_id}")
                print(f"       Type: {data['data'].get('entry_type')}")
                print(f"       Amount: {data['data'].get('amount')} {data['data'].get('currency')}")
        else:
            print_test("Entry creation", False, f"Response: {response.text}")

    except Exception as e:
        print_test("Entry creation", False, f"Error: {str(e)}")


def test_list_entries():
    """Test 8: List Entries"""
    print_header("TEST 8: List Financial Entries")

    try:
        response = requests.get(
            f"{BASE_URL}{API_V1}/entries",
            headers=get_auth_headers()
        )

        print_test("List entries", response.status_code == 200,
                   f"Got: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            if "data" in data:
                entries = data["data"]
                print_test("Entries returned", isinstance(entries, list))
                print(f"       Found {len(entries)} entries")
        else:
            print_test("List entries", False, f"Response: {response.text}")

    except Exception as e:
        print_test("List entries", False, f"Error: {str(e)}")


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
        print(f"{GREEN}{'ALL WORKFLOW TESTS PASSED!'.center(60)}{RESET}")
        print(f"{GREEN}{'='*60}{RESET}\n")
    else:
        print(f"{YELLOW}{'='*60}{RESET}")
        print(f"{YELLOW}{'SOME TESTS FAILED'.center(60)}{RESET}")
        print(f"{YELLOW}{'='*60}{RESET}\n")


if __name__ == "__main__":
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{'TRANSLATRIX PRO - Phase 3+ Workflow Test'.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"\nTesting backend at: {BASE_URL}\n")

    # Login first
    if not login():
        print(f"{RED}Login failed. Cannot proceed with tests.{RESET}")
        exit(1)

    # Run workflow tests
    test_file_upload()
    test_list_files()
    test_get_file_details()
    test_ocr_processing()
    test_translation()
    test_extraction()
    test_create_entry()
    test_list_entries()

    # Print summary
    print_summary()
