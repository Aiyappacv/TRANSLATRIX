"""
File and Ingestion Models
File management, shared links, and batch processing
"""
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SQLEnum, BigInteger, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class IngestionSource(enum.Enum):
    """Source type for ingestion"""
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"
    DROPBOX = "dropbox"
    SFTP = "sftp"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    MANUAL_URL = "manual_url"
    LOCAL_UPLOAD = "local_upload"


class BatchStatus(enum.Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FileStatus(enum.Enum):
    """File processing status"""
    UPLOADED = "uploaded"
    VALIDATING = "validating"
    VALIDATED = "validated"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    CLASSIFYING = "classifying"
    CLASSIFIED = "classified"
    READY_FOR_REVIEW = "ready_for_review"
    COMPLETED = "completed"
    FAILED = "failed"


class SharedLinkSource(Base):
    """Shared link data sources"""
    __tablename__ = "shared_link_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    source_type = Column(SQLEnum(IngestionSource), nullable=False)
    url = Column(Text, nullable=True)
    credentials = Column(Text, nullable=True)  # Encrypted
    config = Column(JSON, nullable=True)  # Source-specific configuration

    is_active = Column(Boolean, nullable=False, default=True)
    last_synced_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class IngestionBatch(Base):
    """Batch of files ingested together"""
    __tablename__ = "ingestion_batches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=True), ForeignKey("shared_link_sources.id"), nullable=True)

    batch_name = Column(String(255), nullable=True)
    status = Column(SQLEnum(BatchStatus), nullable=False, default=BatchStatus.PENDING, index=True)
    total_files = Column(Integer, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    failed_files = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class IngestedFile(Base):
    """Ingested file metadata"""
    __tablename__ = "ingested_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    batch_id = Column(UUID(as_uuid=True), ForeignKey("ingestion_batches.id"), nullable=False, index=True)

    original_filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    # SHA-256 — populated by the background metadata worker, not at upload time.
    checksum = Column(String(64), nullable=True, index=True)
    mime_type = Column(String(100), nullable=True)

    # Storage
    storage_path = Column(String(500), nullable=False)
    storage_url = Column(Text, nullable=True)
    preview_url = Column(Text, nullable=True)

    # Processing
    status = Column(SQLEnum(FileStatus), nullable=False, default=FileStatus.UPLOADED, index=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    virus_scanned = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
