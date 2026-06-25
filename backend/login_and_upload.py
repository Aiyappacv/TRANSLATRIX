import requests

# Step 1: Login to get fresh token
print("Step 1: Logging in...")
login_url = "http://localhost:8000/api/v1/auth/login"
login_data = {
    "email": "carlos@prueba.es",
    "password": "SecurePass123!"
}

login_response = requests.post(login_url, json=login_data)

if login_response.status_code != 200:
    print(f"[ERROR] Login failed: {login_response.json()}")
    exit(1)

token = login_response.json()["access_token"]
print(f"[SUCCESS] Login successful! Got fresh token.")

# Step 2: Upload file
print("\nStep 2: Uploading file...")
upload_url = "http://localhost:8000/api/v1/files/upload"
headers = {"Authorization": f"Bearer {token}"}
file_path = r"C:\Users\Administrator\Desktop\spanish doc1.jpg"

try:
    with open(file_path, 'rb') as f:
        files = {'file': ('spanish_doc1.jpg', f, 'image/jpeg')}
        response = requests.post(upload_url, headers=headers, files=files)

    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        print("\n[SUCCESS] File uploaded successfully!")
        data = response.json()
        print(f"\nFile ID: {data['id']}")
        print(f"Batch ID: {data['batch_id']}")
        print(f"Filename: {data['original_filename']}")
        print(f"File Size: {data['file_size']} bytes")
        print(f"Status: {data['status']}")

        # Save file ID for later use
        with open('file_id.txt', 'w') as f:
            f.write(data['id'])
        print(f"\n[SAVED] File ID saved to file_id.txt for OCR/Translation testing!")
    else:
        print(f"\n[ERROR] Upload failed!")
        print(f"Response: {response.json()}")

except FileNotFoundError:
    print(f"[ERROR] File not found at {file_path}")
except Exception as e:
    print(f"[ERROR] {e}")
