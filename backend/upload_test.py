import requests

token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4MTM5MzQ4OS03MzUyLTQ3YjAtODYxOS04NDI5ZWJhZTQyZDAiLCJlbWFpbCI6ImNhcmxvc0BwcnVlYmEuZXMiLCJleHAiOjE3ODE1NDQ2ODQsImlhdCI6MTc4MTU0Mjg4NCwidHlwZSI6ImFjY2VzcyJ9.aMbkmh5owAaUI40sGdyZGKgZ9QnDkfb2vgtZMIO7feU"
url = "http://localhost:8000/api/v1/files/upload"
headers = {"Authorization": f"Bearer {token}"}
file_path = r"C:\Users\Administrator\Desktop\spanish doc1.jpg"

print(f"Uploading: {file_path}")

try:
    with open(file_path, 'rb') as f:
        files = {'file': ('spanish_doc1.jpg', f, 'image/jpeg')}
        response = requests.post(url, headers=headers, files=files)

    print(f"\nStatus Code: {response.status_code}")
    print(f"\nResponse:")
    print(response.json())

    if response.status_code == 200:
        print("\n✅ File uploaded successfully!")
        data = response.json()
        print(f"File ID: {data['id']}")
        print(f"Batch ID: {data['batch_id']}")
    else:
        print("\n❌ Upload failed!")

except FileNotFoundError:
    print(f"❌ Error: File not found at {file_path}")
except Exception as e:
    print(f"❌ Error: {e}")
