"""
Base Storage Adapter
Abstract interface for object storage providers
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
from io import BytesIO


class StorageConfig(BaseModel):
    """Storage configuration"""
    provider: str  # s3, azure, minio
    bucket_name: str
    region: Optional[str] = None
    endpoint_url: Optional[str] = None
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    connection_string: Optional[str] = None


class BaseStorage(ABC):
    """
    Abstract base class for storage providers
    All storage adapters must implement these methods
    """

    def __init__(self, config: StorageConfig):
        """
        Initialize storage adapter

        Args:
            config: Storage configuration
        """
        self.config = config

    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload file to storage

        Args:
            file_content: File content as bytes
            object_key: Storage path/key for the file
            content_type: MIME type of the file
            metadata: Additional metadata to store with file

        Returns:
            Storage URL or key of uploaded file
        """
        pass

    async def upload_stream(
        self,
        file_path: Path,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> str:
        """
        Upload a file already on local disk to storage, streaming from disk
        rather than buffering the whole thing in memory. Callers write the
        incoming upload to a chunked temp file first (see
        DataIntakeService.register_upload), then hand the path here.

        The base implementation falls back to reading the file into memory
        and calling upload_file() — adapters should override this with a
        true streaming transfer (fput_object / upload_file / shutil.copy)
        whenever the underlying SDK supports it, which all adapters in this
        codebase do.

        Args:
            file_path: Local path of the already-written file
            object_key: Storage path/key for the file
            content_type: MIME type of the file
            metadata: Additional metadata to store with file

        Returns:
            Storage URL or key of uploaded file
        """
        return await self.upload_file(
            file_content=file_path.read_bytes(),
            object_key=object_key,
            content_type=content_type,
            metadata=metadata,
        )

    @abstractmethod
    async def download_file(self, object_key: str) -> bytes:
        """
        Download file from storage

        Args:
            object_key: Storage path/key of the file

        Returns:
            File content as bytes
        """
        pass

    @abstractmethod
    async def delete_file(self, object_key: str) -> bool:
        """
        Delete file from storage

        Args:
            object_key: Storage path/key of the file

        Returns:
            True if deleted successfully
        """
        pass

    @abstractmethod
    async def file_exists(self, object_key: str) -> bool:
        """
        Check if file exists in storage

        Args:
            object_key: Storage path/key of the file

        Returns:
            True if file exists
        """
        pass

    @abstractmethod
    async def get_file_metadata(self, object_key: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata from storage

        Args:
            object_key: Storage path/key of the file

        Returns:
            Metadata dictionary or None if not found
        """
        pass

    @abstractmethod
    async def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        download: bool = False,
    ) -> str:
        """
        Generate a presigned URL for temporary file access

        Args:
            object_key: Storage path/key of the file
            expiration: URL expiration time in seconds
            download: If True, set Content-Disposition for download

        Returns:
            Presigned URL
        """
        pass

    @abstractmethod
    async def copy_file(self, source_key: str, destination_key: str) -> bool:
        """
        Copy file within storage

        Args:
            source_key: Source file key
            destination_key: Destination file key

        Returns:
            True if copied successfully
        """
        pass

    async def get_file_size(self, object_key: str) -> Optional[int]:
        """
        Get file size in bytes

        Args:
            object_key: Storage path/key of the file

        Returns:
            File size in bytes or None if not found
        """
        metadata = await self.get_file_metadata(object_key)
        if metadata:
            return metadata.get("size") or metadata.get("content_length")
        return None

    def build_object_key(
        self,
        tenant_id: str,
        company_id: str,
        filename: str,
        prefix: Optional[str] = None,
    ) -> str:
        """
        Build standardized object key with tenant isolation

        Args:
            tenant_id: Tenant UUID
            company_id: Company UUID
            filename: Original filename
            prefix: Optional prefix (e.g., 'uploads', 'processed')

        Returns:
            Standardized object key
        """
        parts = ["tenants", tenant_id, "companies", company_id]
        if prefix:
            parts.append(prefix)
        parts.append(filename)
        return "/".join(parts)

    def build_document_key(
        self,
        tenant_id: str,
        company_id: str,
        document_uuid: str,
        extension: str,
        category: str = "documents",
        uploaded_at: Optional[datetime] = None,
    ) -> str:
        """
        Build a UUID-named, year/month-partitioned object key.

        Original filenames are never used as storage keys (avoids collisions,
        path-traversal/special-character issues, and leaking filenames into
        object storage) — they're recorded separately in IngestedFile/
        IntakeRegistry.original_filename. Year/month partitioning keeps any
        single storage "directory" from accumulating unbounded object counts
        at enterprise upload volumes.

        Returns e.g. "tenants/<tid>/companies/<cid>/documents/2026/06/<uuid>.pdf"
        """
        when = uploaded_at or datetime.utcnow()
        ext = extension if extension.startswith(".") else f".{extension}" if extension else ""
        return "/".join([
            "tenants", tenant_id, "companies", company_id,
            category, f"{when.year:04d}", f"{when.month:02d}",
            f"{document_uuid}{ext}",
        ])
