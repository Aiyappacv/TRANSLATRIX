from app.config import settings

print(f"STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")
print(f"MINIO_ENDPOINT: {settings.MINIO_ENDPOINT}")
print(f"MINIO_ACCESS_KEY: {settings.MINIO_ACCESS_KEY}")
print(f"MINIO_SECRET_KEY: {settings.MINIO_SECRET_KEY}")
print(f"MINIO_BUCKET: {settings.MINIO_BUCKET}")
print(f"MINIO_SECURE: {settings.MINIO_SECURE}")
