"""
File Schemas
Request/Response models for file operations
"""
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4
from datetime import datetime
from enum import Enum


class FileStatusEnum(str, Enum):
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


class VirusScanStatus(str, Enum):
    """Virus scan status"""
    PENDING = "pending"
    SCANNING = "scanning"
    CLEAN = "clean"
    INFECTED = "infected"
    ERROR = "error"


# File Upload Schemas
class FileUploadResponse(BaseModel):
    """File upload response"""
    id: UUID4
    batch_id: UUID4
    original_filename: str
    file_type: str
    file_size: int
    checksum: str
    storage_path: str
    status: str
    is_duplicate: bool
    virus_scanned: bool
    created_at: datetime

    class Config:
        from_attributes = True


class FileMetadataResponse(BaseModel):
    """File metadata response"""
    id: UUID4
    tenant_id: UUID4
    batch_id: UUID4
    original_filename: str
    file_type: str
    file_size: int
    checksum: str
    mime_type: Optional[str]
    storage_path: str
    storage_url: Optional[str]
    preview_url: Optional[str]
    status: str
    is_duplicate: bool
    virus_scanned: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FileListResponse(BaseModel):
    """List of files"""
    files: List[FileMetadataResponse]
    total: int
    page: int
    page_size: int


class FilePreviewResponse(BaseModel):
    """File preview information"""
    file_id: UUID4
    filename: str
    file_type: str
    preview_url: Optional[str]
    download_url: str
    expires_in: int  # seconds


class FileDownloadResponse(BaseModel):
    """File download URL response"""
    file_id: UUID4
    filename: str
    download_url: str
    expires_in: int  # seconds


class FileValidationResult(BaseModel):
    """File validation result"""
    is_valid: bool
    file_type: str
    file_size: int
    mime_type: str
    errors: List[str] = []
    warnings: List[str] = []


class FileDuplicateCheck(BaseModel):
    """Duplicate file check result"""
    is_duplicate: bool
    checksum: str
    existing_file_id: Optional[UUID4] = None
    existing_filename: Optional[str] = None


class FileProcessingStatus(BaseModel):
    """File processing status"""
    file_id: UUID4
    status: FileStatusEnum
    progress_percentage: int
    current_step: str
    error_message: Optional[str] = None
    updated_at: datetime


# Batch file operations
class BulkDeleteRequest(BaseModel):
    """Bulk delete files request"""
    file_ids: List[UUID4] = Field(..., min_items=1, max_items=100)


class BulkDeleteResponse(BaseModel):
    """Bulk delete response"""
    deleted_count: int
    failed_count: int
    failed_ids: List[UUID4] = []
