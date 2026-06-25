import requests
import sys

print("Testing connection to backend...")
sys.stdout.flush()

try:
    response = requests.get("http://localhost:8000/docs", timeout=5)
    print(f"Status: {response.status_code}")
    print("Backend is reachable!")
except requests.exceptions.ConnectionError as e:
    print(f"Connection error: {e}")
except Exception as e:
    print(f"Error: {e}")

sys.stdout.flush()
