"""
Extraction Schemas
Request and response models for content extraction
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class TableData(BaseModel):
    """Extracted table structure"""
    page: Optional[int] = None
    headers: List[str]
    rows: List[List[Any]]
    metadata: Optional[Dict[str, Any]] = None


class ExtractionRequest(BaseModel):
    """Request to extract content from a file"""
    use_ocr: bool = Field(default=False, description="Force OCR even if native text is available")
    extract_tables: bool = Field(default=True, description="Extract tables from document")
    extract_metadata: bool = Field(default=True, description="Extract document metadata")
    force_reprocess: bool = Field(default=False, description="Force reprocessing even if results exist")


class ExtractionResponse(BaseModel):
    """File content extraction result"""
    id: UUID4
    file_id: UUID4
    method: str
    use_ocr: bool
    status: str
    extracted_text: Optional[str] = None
    extracted_tables: Optional[List[TableData]] = None
    extracted_metadata: Optional[Dict[str, Any]] = None
    confidence_score: Optional[Decimal] = None
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    has_tables: bool
    has_images: bool
    processing_time_seconds: Optional[Decimal] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExtractionStatusResponse(BaseModel):
    """Extraction processing status"""
    status: str
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = None
