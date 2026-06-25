"""
Ingestion Schemas
Request/Response models for file ingestion
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from enum import Enum


class IngestionSourceType(str, Enum):
    """Source types for ingestion"""
    GOOGLE_DRIVE = "google_drive"
    ONEDRIVE = "onedrive"
    SHAREPOINT = "sharepoint"
    DROPBOX = "dropbox"
    SFTP = "sftp"
    AWS_S3 = "aws_s3"
    AZURE_BLOB = "azure_blob"
    MANUAL_URL = "manual_url"
    LOCAL_UPLOAD = "local_upload"


class BatchStatusEnum(str, Enum):
    """Batch processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Shared Link Schemas
class SharedLinkValidateRequest(BaseModel):
    """Validate a shared link"""
    url: str = Field(..., min_length=1)
    source_type: IngestionSourceType
    credentials: Optional[Dict[str, Any]] = None


class SharedLinkValidateResponse(BaseModel):
    """Shared link validation response"""
    is_valid: bool
    source_type: IngestionSourceType
    file_count: Optional[int] = None
    total_size_bytes: Optional[int] = None
    error_message: Optional[str] = None


class SharedLinkCreateRequest(BaseModel):
    """Create a new shared link source"""
    name: str = Field(..., min_length=1, max_length=255)
    source_type: IngestionSourceType
    url: Optional[str] = None
    credentials: Optional[str] = None  # Encrypted credentials JSON
    config: Optional[Dict[str, Any]] = None


class SharedLinkResponse(BaseModel):
    """Shared link source response"""
    id: UUID4
    tenant_id: UUID4
    company_id: UUID4
    name: str
    source_type: str
    url: Optional[str]
    is_active: bool
    last_synced_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SharedLinkListResponse(BaseModel):
    """List of shared link sources"""
    sources: List[SharedLinkResponse]
    total: int


class SharedLinkSyncRequest(BaseModel):
    """Request to sync files from a shared link"""
    file_types: Optional[List[str]] = None
    recursive: bool = True


# Batch Schemas
class BatchCreateRequest(BaseModel):
    """Create a new ingestion batch"""
    source_id: Optional[UUID4] = None
    batch_name: Optional[str] = Field(None, max_length=255)
    file_ids: Optional[List[str]] = None  # External file IDs to ingest


class BatchResponse(BaseModel):
    """Batch processing response"""
    id: UUID4
    tenant_id: UUID4
    company_id: UUID4
    source_id: Optional[UUID4]
    batch_name: Optional[str]
    status: str
    total_files: int
    processed_files: int
    failed_files: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class BatchListResponse(BaseModel):
    """List of batches"""
    batches: List[BatchResponse]
    total: int


class BatchDetailResponse(BaseModel):
    """Detailed batch information with files"""
    batch: BatchResponse
    files: List[Dict[str, Any]]  # List of file details


# File Discovery
class DiscoveredFile(BaseModel):
    """File discovered from source"""
    name: str
    path: str
    size: int
    mime_type: Optional[str]
    modified_at: Optional[datetime]
    source_id: str


class FileDiscoveryResponse(BaseModel):
    """File discovery response"""
    files: List[DiscoveredFile]
    total_count: int
    total_size_bytes: int


# ====== Preprocessing & Tiered Storage ======

class PreprocessingResult(BaseModel):
    fileId: str
    filename: str
    metadata: Dict[str, Any]
    tiers: Dict[str, Dict[str, str]]
    durationMs: int


class LakeTierRecord(BaseModel):
    id: str
    fileId: str
    tier: str
    storageKey: str
    checksum: str
    contentType: Optional[str]
    sizeBytes: int
    metadataJson: Optional[Dict[str, Any]]
    createdAt: datetime

    class Config:
        from_attributes = True


class ProcessingAuditResponse(BaseModel):
    id: str
    fileId: str
    step: str
    status: str
    message: Optional[str]
    durationMs: Optional[int]
    metadataJson: Optional[Dict[str, Any]]
    createdAt: datetime

    class Config:
        from_attributes = True


# ====== Deduplication ======

class DedupMatch(BaseModel):
    fileId: str
    filename: str
    similarity: float
    method: str


class DedupResult(BaseModel):
    isDuplicate: bool
    similarityScore: float
    matches: List[DedupMatch]
    embeddingId: Optional[str] = None


# ====== Document Preview ======

class PreviewPage(BaseModel):
    pageNumber: int
    imageUrl: str
    width: int
    height: int


class PreviewInfo(BaseModel):
    fileId: str
    filename: str
    contentType: str
    sizeBytes: int
    totalPages: int
    pages: List[PreviewPage]
    previewToken: str
    expiresAt: str


# ====== Extraction ======

class ExtractedField(BaseModel):
    name: str
    value: Any
    confidence: float
    pageNumber: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None


class ExtractionResult(BaseModel):
    fileId: str
    filename: str
    fields: List[ExtractedField]
    rawText: str
    confidence: float
    processingTimeMs: int
    ocrEngine: str


class ExtractionJobResponse(BaseModel):
    jobId: str
    fileId: str
    status: str
    result: Optional[ExtractionResult] = None
    error: Optional[str] = None


# ====== JSON Export ======

class ExportRequest(BaseModel):
    fileIds: List[UUID4]
    includeRawText: bool = True
    includeMetadata: bool = True
    includeConfidence: bool = False


class ExportFile(BaseModel):
    fileId: str
    filename: str
    extractedAt: str
    fields: List[ExtractedField]
    rawText: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ExportResponse(BaseModel):
    exportId: str
    exportedAt: str
    totalFiles: int
    files: List[ExportFile]
    jsonPayload: str
