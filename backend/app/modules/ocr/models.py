"""
OCR Models
PaddleOCR and other OCR provider results storage
"""
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class OCRProvider(enum.Enum):
    """OCR provider types"""
    MISTRAL = "mistral"
    PADDLEOCR = "paddleocr"
    AZURE_DI = "azure_di"
    AWS_TEXTRACT = "aws_textract"
    GOOGLE_VISION = "google_vision"


class OCRStatus(enum.Enum):
    """OCR processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class OCRResult(Base):
    """OCR processing results for files"""
    __tablename__ = "ocr_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("ingested_files.id"), nullable=False, unique=True)

    # OCR configuration
    provider = Column(SQLEnum(OCRProvider), nullable=False, default=OCRProvider.MISTRAL)
    language = Column(String(10), nullable=True, default="en")  # ISO 639-1 language code

    # Processing status
    status = Column(SQLEnum(OCRStatus), nullable=False, default=OCRStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)

    # Results metadata
    total_pages = Column(Integer, nullable=True)
    average_confidence = Column(Numeric(5, 2), nullable=True)
    processing_time_seconds = Column(Numeric(10, 2), nullable=True)

    # Full extracted text (combined from all pages)
    full_text = Column(Text, nullable=True)

    # Provider-specific metadata
    provider_metadata = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


class OCRPage(Base):
    """Page-level OCR data with bounding boxes"""
    __tablename__ = "ocr_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocr_result_id = Column(UUID(as_uuid=True), ForeignKey("ocr_results.id"), nullable=False, index=True)

    page_number = Column(Integer, nullable=False)

    # Extracted text for this page
    text = Column(Text, nullable=True)
    confidence = Column(Numeric(5, 2), nullable=True)

    # Structured OCR data with bounding boxes
    # Format: [{"text": "...", "confidence": 0.99, "bbox": [x1, y1, x2, y2]}, ...]
    text_blocks = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)

    # Page dimensions
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
