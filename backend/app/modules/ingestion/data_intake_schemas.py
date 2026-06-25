from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class IntakeRegistryEntry(BaseModel):
    id: str
    file_id: Optional[str] = None
    original_filename: str
    source_channel: str
    document_type: Optional[str] = None
    language: Optional[str] = None
    status: str
    tier: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of_id: Optional[str] = None
    duplicate_similarity: Optional[float] = None
    checksum: Optional[str] = None
    file_size: int = 0
    mime_type: Optional[str] = None
    page_count: Optional[int] = None
    language_detected: Optional[str] = None
    orientation: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DuplicateMatch(BaseModel):
    file_id: str
    registry_id: Optional[str] = None
    filename: str
    similarity: float
    method: str
    uploaded_at: Optional[datetime] = None


class DuplicateWarning(BaseModel):
    is_exact_duplicate: bool = False
    is_semantic_duplicate: bool = False
    similarity_score: float = 0.0
    matches: List[DuplicateMatch] = []


class IntakeRegistryListResponse(BaseModel):
    entries: List[IntakeRegistryEntry]
    total: int


class UploadResponse(BaseModel):
    entry: IntakeRegistryEntry
    duplicate_warning: Optional[DuplicateWarning] = None


class CheckDuplicateRequest(BaseModel):
    filename: str
    file_size: int = 0
    content_type: Optional[str] = None


class CheckDuplicateResponse(BaseModel):
    is_exact_duplicate: bool = False
    is_semantic_duplicate: bool = False
    similarity_score: float = 0.0
    matches: List[DuplicateMatch] = []


class PreviewPage(BaseModel):
    page_number: int
    image_url: str
    width: int = 0
    height: int = 0


class PreviewResponse(BaseModel):
    entry_id: str
    filename: str
    mime_type: str
    file_size: int
    total_pages: int
    pages: List[PreviewPage] = []


class ExtractNavigationResponse(BaseModel):
    file_id: str
    entry_id: str
    redirect_url: str


class DeleteResponse(BaseModel):
    deleted: bool
    message: str


class IntakeEventResponse(BaseModel):
    id: str
    registry_id: str
    event_type: str
    status: str
    message: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BatchJobProgress(BaseModel):
    job_id: str
    job_type: str
    status: str
    payload: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    file_name: Optional[str] = None


class BatchProgressResponse(BaseModel):
    batch_id: str
    total: int = 0
    queued: int = 0
    processing: int = 0
    completed: int = 0
    failed: int = 0
    jobs: List[BatchJobProgress] = []


class RetryExtractionResponse(BaseModel):
    entry_id: str
    status: str
    message: str


class BulkDeleteRequest(BaseModel):
    entry_ids: List[str]


class BulkDeleteResponse(BaseModel):
    deleted: int
    message: str
