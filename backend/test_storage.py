"""Test storage configuration directly"""
import sys
sys.path.insert(0, '.')

from app.config import settings
from app.modules.storage.adapters.base import StorageConfig
from app.modules.storage.adapters.minio import MinIOStorage

print(f"Storage Provider: {settings.STORAGE_PROVIDER}")
print(f"MINIO_ENDPOINT: {settings.MINIO_ENDPOINT}")
print(f"MINIO_BUCKET: {settings.MINIO_BUCKET}")
print(f"MINIO_ACCESS_KEY: {settings.MINIO_ACCESS_KEY}")
print(f"MINIO_SECURE: {settings.MINIO_SECURE}")

# Build endpoint URL like in service.py
endpoint_url = settings.MINIO_ENDPOINT
if endpoint_url and not endpoint_url.startswith("http"):
    protocol = "https" if settings.MINIO_SECURE else "http"
    endpoint_url = f"{protocol}://{endpoint_url}"

print(f"\nBuilt endpoint_url: {endpoint_url}")

# Create config
config = StorageConfig(
    provider="minio",
    bucket_name=settings.MINIO_BUCKET or "translatrix-pro",
    endpoint_url=endpoint_url,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
)

print(f"\nStorageConfig created:")
print(f"  provider: {config.provider}")
print(f"  bucket_name: {config.bucket_name}")
print(f"  endpoint_url: {config.endpoint_url}")
print(f"  access_key: {config.access_key}")

# Try to create MinIO storage
print("\nCreating MinIOStorage...")
storage = MinIOStorage(config)
print("MinIOStorage created successfully!")

# Try to get client
print("\nGetting MinIO client...")
try:
    client = storage._get_client()
    print("MinIO client created successfully!")
    print(f"Client endpoint: {client._base_url}")
except Exception as e:
    print(f"ERROR creating client: {e}")
