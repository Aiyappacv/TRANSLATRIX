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

# Step 3: Trigger Content Extraction
print("\nStep 3: Triggering content extraction...")
extraction_url = f"http://localhost:8000/api/v1/files/{file_id}/extract"
headers = {"Authorization": f"Bearer {token}"}
extraction_data = {
    "use_ocr": True,
    "extract_tables": True,
    "extract_metadata": True,
    "force_reprocess": False
}

try:
    response = requests.post(extraction_url, headers=headers, json=extraction_data, timeout=120)

    print(f"\nStatus Code: {response.status_code}")
    print(f"Response Text: {response.text[:500]}")  # Show first 500 chars of response

    if response.status_code in [200, 201, 202]:
        print("\n[SUCCESS] Content extraction completed!")
        data = response.json()

        if 'data' in data:
            extraction_result = data['data']
            print(f"\nExtraction Result:")
            print(f"ID: {extraction_result.get('id')}")
            print(f"Status: {extraction_result.get('status')}")
            print(f"Method: {extraction_result.get('method')}")
            print(f"Page Count: {extraction_result.get('page_count')}")
            print(f"Word Count: {extraction_result.get('word_count')}")
            print(f"Has Tables: {extraction_result.get('has_tables')}")
            print(f"Has Images: {extraction_result.get('has_images')}")

            # Show extracted text preview
            if 'extracted_text' in extraction_result and extraction_result['extracted_text']:
                text = extraction_result['extracted_text']
                print(f"\nExtracted Text Preview (first 500 chars):")
                print(f"{text[:500]}...")

            # Show extracted tables
            if 'extracted_tables' in extraction_result and extraction_result['extracted_tables']:
                tables = extraction_result['extracted_tables']
                print(f"\nExtracted {len(tables)} tables")

            # Save extraction result ID for later use
            if 'id' in extraction_result:
                with open('extraction_id.txt', 'w') as f:
                    f.write(extraction_result['id'])
                print(f"\n[SAVED] Extraction ID saved to extraction_id.txt!")
        else:
            print(f"\nResponse data: {data}")
    else:
        print(f"\n[ERROR] Content extraction failed!")
        print(f"Response: {response.json()}")

except requests.exceptions.Timeout:
    print(f"\n[ERROR] Request timed out after 120 seconds")
except Exception as e:
    print(f"\n[ERROR] {e}")
