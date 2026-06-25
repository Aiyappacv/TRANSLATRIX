"""
Storage Adapters Package
Abstraction layer for different storage providers
"""
from app.modules.storage.adapters.base import BaseStorage, StorageConfig
from app.modules.storage.adapters.s3 import S3Storage
from app.modules.storage.adapters.azure import AzureBlobStorage
from app.modules.storage.adapters.minio import MinIOStorage

__all__ = [
    "BaseStorage",
    "StorageConfig",
    "S3Storage",
    "AzureBlobStorage",
    "MinIOStorage",
]
