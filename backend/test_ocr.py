import requests

# File ID from the uploaded test file
FILE_ID = "e187f20d-f25a-4a7d-b8f8-4a0c14b0f8aa"

# Step 1: Login to get token
print("Step 1: Logging in...")
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "email": "admin-unique123@testcorp.com",
    "password": "AdminPass123"
}

login_response = requests.post(login_url, json=login_data)

if login_response.status_code != 200:
    print(f"[ERROR] Login failed: {login_response.json()}")
    exit(1)

token = login_response.json()["access_token"]
print(f"[SUCCESS] Login successful!")

# Step 2: Use the uploaded file ID
print(f"\nStep 2: Using file ID: {FILE_ID}")
file_id = FILE_ID

# Step 3: Trigger OCR processing
print("\nStep 3: Triggering OCR processing (English language)...")
ocr_url = f"http://localhost:8000/api/v1/files/{file_id}/ocr"
headers = {"Authorization": f"Bearer {token}"}
ocr_data = {
    "provider": "mistral",
    "language": "en",
    "force_reprocess": True  # Force reprocess to test the fix
}

try:
    response = requests.post(ocr_url, headers=headers, json=ocr_data, timeout=120)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        print("\n[SUCCESS] OCR processing completed!")
        data = response.json()

        if 'data' in data:
            ocr_result = data['data']
            print(f"\nOCR Result ID: {ocr_result.get('id')}")
            print(f"Provider: {ocr_result.get('provider')}")
            print(f"Language: {ocr_result.get('language')}")
            print(f"Confidence: {ocr_result.get('confidence_score')}")

            if 'pages' in ocr_result:
                print(f"\nPages extracted: {len(ocr_result['pages'])}")
                for i, page in enumerate(ocr_result['pages'], 1):
                    print(f"\n--- Page {i} ---")
                    print(f"Text length: {len(page.get('text', ''))} characters")
                    print(f"First 200 chars: {page.get('text', '')[:200]}...")

            # Save OCR result ID for translation
            if 'id' in ocr_result:
                with open('ocr_id.txt', 'w') as f:
                    f.write(ocr_result['id'])
                print(f"\n[SAVED] OCR ID saved to ocr_id.txt!")
        else:
            print(f"\nResponse data: {data}")
    else:
        print(f"\n[ERROR] OCR processing failed!")
        print(f"Response: {response.json()}")

except requests.exceptions.Timeout:
    print(f"\n[ERROR] Request timed out after 120 seconds")
except Exception as e:
    print(f"\n[ERROR] {e}")
