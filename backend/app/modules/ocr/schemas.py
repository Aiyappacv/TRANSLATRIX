"""
OCR Schemas
Request and response models for OCR operations
"""
from pydantic import BaseModel, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal


class TextBlock(BaseModel):
    """Single text block with bounding box"""
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: List[float] = Field(..., description="Bounding box [x1, y1, x2, y2]")


class OCRPageData(BaseModel):
    """OCR data for a single page"""
    page_number: int
    text: str
    confidence: float
    text_blocks: List[TextBlock]
    width: Optional[int] = None
    height: Optional[int] = None


class OCRRequest(BaseModel):
    """Request to perform OCR on a file"""
    provider: str = Field(default="mistral", description="OCR provider to use")
    language: str = Field(default="en", description="Language code (ISO 639-1)")
    force_reprocess: bool = Field(default=False, description="Force reprocessing even if results exist")


class OCRResponse(BaseModel):
    """OCR processing result"""
    id: UUID4
    file_id: UUID4
    provider: str
    language: str
    status: str
    total_pages: Optional[int] = None
    average_confidence: Optional[Decimal] = None
    processing_time_seconds: Optional[Decimal] = None
    full_text: Optional[str] = None
    pages: Optional[List[OCRPageData]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OCRStatusResponse(BaseModel):
    """OCR processing status"""
    status: str
    progress: Optional[int] = Field(None, description="Progress percentage (0-100)")
    message: Optional[str] = None
