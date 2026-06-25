"""
Debug script to test storage configuration
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

print("=" * 60)
print("STORAGE CONFIGURATION DEBUG")
print("=" * 60)

# Test 1: Load config
print("\n1. Loading configuration...")
try:
    from app.config import settings
    print(f"   [OK] Config loaded successfully")
    print(f"   STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")
    print(f"   MINIO_ENDPOINT: {settings.MINIO_ENDPOINT}")
    print(f"   MINIO_BUCKET: {settings.MINIO_BUCKET}")
    print(f"   MINIO_SECURE: {settings.MINIO_SECURE}")
except Exception as e:
    print(f"   [FAIL] Config load failed: {e}")
    sys.exit(1)

# Test 2: Import minio
print("\n2. Testing minio package import...")
try:
    from minio import Minio
    print(f"   [OK] minio package imports successfully")
except ImportError as e:
    print(f"   [FAIL] minio import failed: {e}")
    sys.exit(1)

# Test 3: Create MinIO client
print("\n3. Testing MinIO client creation...")
try:
    endpoint = settings.MINIO_ENDPOINT
    if not endpoint.startswith("http"):
        protocol = "https" if settings.MINIO_SECURE else "http"
        endpoint_with_protocol = f"{protocol}://{endpoint}"
    else:
        endpoint_with_protocol = endpoint

    # Remove protocol for Minio client
    endpoint_clean = endpoint.replace("http://", "").replace("https://", "")

    print(f"   Raw endpoint: {endpoint}")
    print(f"   Clean endpoint: {endpoint_clean}")
    print(f"   Secure: {settings.MINIO_SECURE}")

    client = Minio(
        endpoint_clean,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    print(f"   [OK] MinIO client created successfully")
except Exception as e:
    print(f"   [FAIL] MinIO client creation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Check bucket
print("\n4. Testing bucket access...")
try:
    bucket_name = settings.MINIO_BUCKET or "translatrix-pro"
    exists = client.bucket_exists(bucket_name)
    print(f"   Bucket '{bucket_name}' exists: {exists}")

    if not exists:
        print(f"   Creating bucket '{bucket_name}'...")
        client.make_bucket(bucket_name)
        print(f"   [OK] Bucket created successfully")
    else:
        print(f"   [OK] Bucket already exists")
except Exception as e:
    print(f"   [FAIL] Bucket check failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Test file upload
print("\n5. Testing file upload...")
try:
    from io import BytesIO
    test_content = b"Hello, MinIO! This is a test file."
    test_stream = BytesIO(test_content)

    client.put_object(
        bucket_name,
        "test_upload.txt",
        test_stream,
        len(test_content),
        content_type="text/plain"
    )
    print(f"   [OK] File uploaded successfully")

    # Clean up
    client.remove_object(bucket_name, "test_upload.txt")
    print(f"   [OK] Test file removed")
except Exception as e:
    print(f"   [FAIL] File upload failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("ALL TESTS PASSED!")
print("=" * 60)
print("\nStorage is configured correctly. The issue may be:")
print("1. Server needs to be restarted to pick up changes")
print("2. A different error is being caught and misreported")
print("\nNext steps:")
print("1. Stop the server (Ctrl+C or taskkill)")
print("2. Restart: python -m uvicorn app.main:app --reload")
print("3. Try file upload again")
