"""
File Service
File upload, validation, and storage management
"""
from typing import List, Optional, Tuple, BinaryIO
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime
import structlog
from uuid import UUID
import hashlib
import mimetypes
import os

from app.modules.files.models import IngestedFile, FileStatus, IngestionBatch, BatchStatus
from app.modules.files.schemas import (
    FileMetadataResponse,
    FileValidationResult,
    FileDuplicateCheck,
)
from app.modules.storage.adapters.base import BaseStorage, StorageConfig
from app.modules.storage.adapters.s3 import S3Storage
from app.modules.storage.adapters.azure import AzureBlobStorage
from app.modules.storage.adapters.minio import MinIOStorage
from app.config import settings

logger = structlog.get_logger(__name__)


class FileService:
    """Service for file operations"""

    def __init__(self, db: Session):
        self.db = db
        self._storage: Optional[BaseStorage] = None

    def _get_storage(self) -> BaseStorage:
        """
        Get storage adapter based on configuration
        """
        if self._storage is None:
            try:
                if settings.STORAGE_PROVIDER == "minio":
                    # Build MinIO endpoint URL
                    endpoint_url = settings.MINIO_ENDPOINT
                    logger.info("minio_config", raw_endpoint=endpoint_url, secure=settings.MINIO_SECURE)
                    if endpoint_url and not endpoint_url.startswith("http"):
                        protocol = "https" if settings.MINIO_SECURE else "http"
                        endpoint_url = f"{protocol}://{endpoint_url}"

                    logger.info("minio_storage_config",
                               endpoint_url=endpoint_url,
                               bucket=settings.MINIO_BUCKET,
                               has_access_key=bool(settings.MINIO_ACCESS_KEY))

                    config = StorageConfig(
                        provider="minio",
                        bucket_name=settings.MINIO_BUCKET or "translatrix-pro",
                        endpoint_url=endpoint_url,
                        access_key=settings.MINIO_ACCESS_KEY,
                        secret_key=settings.MINIO_SECRET_KEY,
                    )
                    self._storage = MinIOStorage(config)
                elif settings.STORAGE_PROVIDER == "s3":
                    config = StorageConfig(
                        provider="s3",
                        bucket_name=settings.S3_BUCKET_NAME,
                        region=settings.AWS_REGION,
                        access_key=settings.AWS_ACCESS_KEY_ID,
                        secret_key=settings.AWS_SECRET_ACCESS_KEY,
                    )
                    self._storage = S3Storage(config)
                elif settings.STORAGE_PROVIDER == "azure":
                    config = StorageConfig(
                        provider="azure",
                        bucket_name=settings.AZURE_CONTAINER_NAME or "translatrix-files",
                        connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
                    )
                    self._storage = AzureBlobStorage(config)
                else:
                    # Unsupported or missing storage provider — fallback to local
                    raise ValueError(f"Unsupported storage provider: {settings.STORAGE_PROVIDER}")
            except Exception as e:
                logger.warning("storage_adapter_init_failed", error=str(e), provider=settings.STORAGE_PROVIDER)
                # Fall back to local storage to allow uploads to continue even when remote storage
                # configuration is missing or invalid. This is safer for development and recovery.
                from app.modules.storage.adapters.local import LocalStorage

                config = StorageConfig(provider="local", bucket_name=settings.LOCAL_STORAGE_DIR or "local")
                self._storage = LocalStorage(config)

        return self._storage

    def calculate_checksum(self, file_content: bytes) -> str:
        """
        Calculate SHA-256 checksum of file content

        Args:
            file_content: File content as bytes

        Returns:
            SHA-256 hash as hex string
        """
        return hashlib.sha256(file_content).hexdigest()

    def validate_file(
        self,
        filename: str,
        file_size: int,
        file_content: bytes,
    ) -> FileValidationResult:
        """
        Validate file before upload

        Args:
            filename: Original filename
            file_size: File size in bytes
            file_content: File content for mime type detection

        Returns:
            Validation result with errors/warnings
        """
        errors = []
        warnings = []

        # Get file extension
        file_ext = os.path.splitext(filename)[1].lower().lstrip(".")

        # Check file type
        if file_ext not in settings.allowed_file_types_list:
            errors.append(
                f"File type '.{file_ext}' not allowed. Allowed types: {', '.join(settings.allowed_file_types_list)}"
            )

        # Check file size
        if file_size > settings.max_file_size_bytes:
            errors.append(
                f"File size {file_size} bytes exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
            )

        if file_size == 0:
            errors.append("File is empty")

        # Detect mime type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/octet-stream"
            warnings.append("Could not detect MIME type")

        is_valid = len(errors) == 0

        return FileValidationResult(
            is_valid=is_valid,
            file_type=file_ext,
            file_size=file_size,
            mime_type=mime_type,
            errors=errors,
            warnings=warnings,
        )

    def check_duplicate(
        self, checksum: str, tenant_id: UUID
    ) -> FileDuplicateCheck:
        """
        Check if file with same checksum already exists

        Args:
            checksum: SHA-256 checksum
            tenant_id: Tenant ID for isolation

        Returns:
            Duplicate check result
        """
        existing_file = (
            self.db.query(IngestedFile)
            .filter(
                IngestedFile.checksum == checksum,
                IngestedFile.tenant_id == tenant_id,
            )
            .first()
        )

        if existing_file:
            return FileDuplicateCheck(
                is_duplicate=True,
                checksum=checksum,
                existing_file_id=existing_file.id,
                existing_filename=existing_file.original_filename,
            )

        return FileDuplicateCheck(
            is_duplicate=False,
            checksum=checksum,
        )

    async def upload_file(
        self,
        tenant_id: UUID,
        batch_id: UUID,
        filename: str,
        file_content: bytes,
        allow_duplicates: bool = False,
    ) -> IngestedFile:
        """
        Upload file to storage and create database record

        Args:
            tenant_id: Tenant ID
            batch_id: Batch ID for grouping
            filename: Original filename
            file_content: File content as bytes
            allow_duplicates: Whether to allow duplicate files

        Returns:
            Created file record

        Raises:
            ValueError: If validation fails
        """
        logger.info(
            "uploading_file",
            tenant_id=str(tenant_id),
            batch_id=str(batch_id),
            filename=filename,
            size=len(file_content),
        )

        # Validate file
        validation = self.validate_file(filename, len(file_content), file_content)
        if not validation.is_valid:
            raise ValueError(f"File validation failed: {', '.join(validation.errors)}")

        # Calculate checksum
        checksum = self.calculate_checksum(file_content)

        # Check for duplicates
        duplicate_check = self.check_duplicate(checksum, tenant_id)
        is_duplicate = duplicate_check.is_duplicate

        if is_duplicate and not allow_duplicates:
            logger.warning(
                "duplicate_file_detected",
                checksum=checksum,
                existing_file_id=str(duplicate_check.existing_file_id),
            )
            # Return existing file instead of uploading again
            existing_file = self.db.query(IngestedFile).filter(
                IngestedFile.id == duplicate_check.existing_file_id
            ).first()
            return existing_file

        # Get batch and company_id
        batch = self.db.query(IngestionBatch).filter(IngestionBatch.id == batch_id).first()
        if not batch:
            raise ValueError("Batch not found")

        # Build storage path
        storage = self._get_storage()
        storage_path = storage.build_object_key(
            tenant_id=str(tenant_id),
            company_id=str(batch.company_id),
            filename=f"{checksum}_{filename}",
            prefix="uploads",
        )

        # Upload to storage
        try:
            await storage.upload_file(
                file_content=file_content,
                object_key=storage_path,
                content_type=validation.mime_type,
                metadata={
                    "original_filename": filename,
                    "tenant_id": str(tenant_id),
                    "batch_id": str(batch_id),
                    "checksum": checksum,
                },
            )

            logger.info("file_uploaded_to_storage", storage_path=storage_path)

        except Exception as e:
            logger.error("storage_upload_failed", error=str(e))
            raise ValueError(f"Failed to upload file to storage: {str(e)}")

        # Create database record
        file_record = IngestedFile(
            tenant_id=tenant_id,
            batch_id=batch_id,
            original_filename=filename,
            file_type=validation.file_type,
            file_size=validation.file_size,
            checksum=checksum,
            mime_type=validation.mime_type,
            storage_path=storage_path,
            status=FileStatus.UPLOADED,
            is_duplicate=is_duplicate,
            virus_scanned=False,  # Will be updated by virus scan service
        )

        self.db.add(file_record)

        # Update batch file count
        batch.total_files = batch.total_files + 1
        batch.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(file_record)

        logger.info("file_record_created", file_id=str(file_record.id))
        return file_record

    def list_files(
        self,
        tenant_id: UUID,
        company_id: Optional[UUID] = None,
        batch_id: Optional[UUID] = None,
        status: Optional[FileStatus] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[IngestedFile], int]:
        """
        List files with filtering and pagination
        """
        query = self.db.query(IngestedFile).filter(IngestedFile.tenant_id == tenant_id)

        if batch_id:
            query = query.filter(IngestedFile.batch_id == batch_id)

        if status:
            query = query.filter(IngestedFile.status == status)

        total = query.count()

        files = (
            query.order_by(desc(IngestedFile.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return files, total

    def get_file(self, file_id: UUID, tenant_id: UUID) -> Optional[IngestedFile]:
        """
        Get file by ID with tenant isolation
        """
        return (
            self.db.query(IngestedFile)
            .filter(
                IngestedFile.id == file_id,
                IngestedFile.tenant_id == tenant_id,
            )
            .first()
        )

    async def generate_download_url(
        self, file_id: UUID, tenant_id: UUID, expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate signed download URL for file
        """
        file = self.get_file(file_id, tenant_id)
        if not file:
            return None

        storage = self._get_storage()

        try:
            url = await storage.generate_presigned_url(
                object_key=file.storage_path,
                expiration=expiration,
                download=True,
            )
            return url
        except Exception as e:
            logger.error("generate_download_url_failed", error=str(e), file_id=str(file_id))
            return None

    async def generate_preview_url(
        self, file_id: UUID, tenant_id: UUID, expiration: int = 3600
    ) -> Optional[str]:
        """
        Generate signed preview URL for file
        """
        file = self.get_file(file_id, tenant_id)
        if not file:
            return None

        storage = self._get_storage()

        try:
            url = await storage.generate_presigned_url(
                object_key=file.storage_path,
                expiration=expiration,
                download=False,
            )
            return url
        except Exception as e:
            logger.error("generate_preview_url_failed", error=str(e), file_id=str(file_id))
            return None

    async def delete_file(self, file_id: UUID, tenant_id: UUID) -> bool:
        """
        Delete file from storage and database
        """
        logger.info("deleting_file", file_id=str(file_id))

        file = self.get_file(file_id, tenant_id)
        if not file:
            return False

        storage = self._get_storage()

        # Delete from storage
        try:
            await storage.delete_file(file.storage_path)
            logger.info("file_deleted_from_storage", storage_path=file.storage_path)
        except Exception as e:
            logger.error("storage_delete_failed", error=str(e), file_id=str(file_id))
            # Continue with database deletion even if storage deletion fails

        # Delete from database
        self.db.delete(file)

        # Update batch file count
        batch = self.db.query(IngestionBatch).filter(IngestionBatch.id == file.batch_id).first()
        if batch and batch.total_files > 0:
            batch.total_files = batch.total_files - 1
            batch.updated_at = datetime.utcnow()

        self.db.commit()

        logger.info("file_deleted", file_id=str(file_id))
        return True

    async def download_file(self, file_id: UUID, tenant_id: UUID) -> Optional[bytes]:
        """
        Download file content from storage
        """
        file = self.get_file(file_id, tenant_id)
        if not file:
            return None

        storage = self._get_storage()

        try:
            content = await storage.download_file(file.storage_path)
            return content
        except Exception as e:
            logger.error("file_download_failed", error=str(e), file_id=str(file_id))
            return None
