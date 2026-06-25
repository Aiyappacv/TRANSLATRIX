"""
Comprehensive OCR Endpoints Test
Tests all OCR endpoints:
1. POST /api/v1/files/{file_id}/ocr - Process File OCR
2. GET /api/v1/files/{file_id}/ocr - Get OCR Result
3. GET /api/v1/files/{file_id}/ocr/status - Get OCR Status
"""
import requests
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_V1 = "/api/v1"
FILE_ID = "e187f20d-f25a-4a7d-b8f8-4a0c14b0f8aa"  # From uploaded test file

# Test credentials
TEST_EMAIL = "admin-unique123@testcorp.com"
TEST_PASSWORD = "AdminPass123"

print("="*70)
print("OCR ENDPOINTS TEST SUITE")
print("="*70)

# Step 1: Login
print("\n[STEP 1] Logging in...")
login_response = requests.post(
    f"{BASE_URL}{API_V1}/auth/login",
    json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
)

if login_response.status_code != 200:
    print(f"[FAIL] Login failed: {login_response.json()}")
    exit(1)

token = login_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"[OK] Login successful!")

# Step 2: POST - Process File OCR
print("\n" + "="*70)
print("[STEP 2] POST /api/v1/files/{file_id}/ocr - Process File OCR")
print("="*70)

ocr_request = {
    "provider": "mistral",
    "language": "en",
    "force_reprocess": False
}

print(f"Request payload: {ocr_request}")
ocr_response = requests.post(
    f"{BASE_URL}{API_V1}/files/{FILE_ID}/ocr",
    headers=headers,
    json=ocr_request,
    timeout=120
)

print(f"\nStatus Code: {ocr_response.status_code}")

if ocr_response.status_code == 200:
    print("[OK] OCR processing completed!")
    data = ocr_response.json()

    if 'data' in data:
        ocr_result = data['data']
        print(f"\nOCR Result Details:")
        print(f"  ID: {ocr_result.get('id')}")
        print(f"  Provider: {ocr_result.get('provider')}")
        print(f"  Language: {ocr_result.get('language')}")
        print(f"  Status: {ocr_result.get('status')}")
        print(f"  Confidence: {ocr_result.get('confidence_score')}")

        if 'pages' in ocr_result and ocr_result['pages']:
            pages = ocr_result['pages']
            print(f"\n  Pages extracted: {len(pages)}")
            for i, page in enumerate(pages[:2], 1):  # Show first 2 pages
                print(f"\n  --- Page {i} ---")
                print(f"  Page Number: {page.get('page_number')}")
                print(f"  Text Preview: {page.get('text', '')[:150]}...")

        ocr_result_id = ocr_result.get('id')
else:
    print(f"[FAIL] OCR processing failed!")
    print(f"Response: {ocr_response.text[:500]}")
    ocr_result_id = None

# Step 3: GET - Get OCR Result
print("\n" + "="*70)
print("[STEP 3] GET /api/v1/files/{file_id}/ocr - Get OCR Result")
print("="*70)

get_result_response = requests.get(
    f"{BASE_URL}{API_V1}/files/{FILE_ID}/ocr",
    headers=headers
)

print(f"\nStatus Code: {get_result_response.status_code}")

if get_result_response.status_code == 200:
    print("[OK] OCR result retrieved successfully!")
    data = get_result_response.json()

    if 'data' in data:
        ocr_data = data['data']
        print(f"\nRetrieved OCR Result:")
        print(f"  ID: {ocr_data.get('id')}")
        print(f"  Status: {ocr_data.get('status')}")
        print(f"  Total Pages: {ocr_data.get('total_pages')}")
        print(f"  Average Confidence: {ocr_data.get('average_confidence')}")
        print(f"  Processing Time: {ocr_data.get('processing_time_seconds')}s")

        if 'pages' in ocr_data:
            print(f"  Pages available: {len(ocr_data['pages'])}")
else:
    print(f"[FAIL] Failed to retrieve OCR result!")
    print(f"Response: {get_result_response.text[:500]}")

# Step 4: GET - Get OCR Status
print("\n" + "="*70)
print("[STEP 4] GET /api/v1/files/{file_id}/ocr/status - Get OCR Status")
print("="*70)

status_response = requests.get(
    f"{BASE_URL}{API_V1}/files/{FILE_ID}/ocr/status",
    headers=headers
)

print(f"\nStatus Code: {status_response.status_code}")

if status_response.status_code == 200:
    print("[OK] OCR status retrieved successfully!")
    data = status_response.json()

    if 'data' in data:
        status_data = data['data']
        print(f"\nOCR Processing Status:")
        print(f"  Status: {status_data.get('status')}")
        print(f"  Progress: {status_data.get('progress')}%")
        if status_data.get('message'):
            print(f"  Message: {status_data.get('message')}")
else:
    print(f"[FAIL] Failed to retrieve OCR status!")
    print(f"Response: {status_response.text[:500]}")

# Summary
print("\n" + "="*70)
print("TEST SUMMARY")
print("="*70)
print(f"POST /ocr:        {'PASS' if ocr_response.status_code == 200 else 'FAIL'}")
print(f"GET /ocr:         {'PASS' if get_result_response.status_code == 200 else 'FAIL'}")
print(f"GET /ocr/status:  {'PASS' if status_response.status_code == 200 else 'FAIL'}")
print("="*70)
