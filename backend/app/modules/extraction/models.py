"""
Extraction Models
File content extraction metadata and results
"""
from sqlalchemy import Column, String, DateTime, Numeric, Integer, Text, ForeignKey, Boolean, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class ExtractionMethod(enum.Enum):
    """Content extraction method"""
    NATIVE_TEXT = "native_text"  # PDF/DOCX native text extraction
    OCR = "ocr"  # OCR-based extraction
    HYBRID = "hybrid"  # Combination of native and OCR
    SPREADSHEET = "spreadsheet"  # Excel/CSV parsing


class ExtractionStatus(enum.Enum):
    """Extraction processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileExtractionResult(Base):
    """File content extraction results"""
    __tablename__ = "file_extraction_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("ingested_files.id"), nullable=False, unique=True)

    # Extraction configuration
    method = Column(SQLEnum(ExtractionMethod), nullable=False)
    use_ocr = Column(Boolean, nullable=False, default=False)

    # Processing status
    status = Column(SQLEnum(ExtractionStatus), nullable=False, default=ExtractionStatus.PENDING, index=True)
    error_message = Column(Text, nullable=True)

    # Extracted content
    extracted_text = Column(Text, nullable=True)
    extracted_tables = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)  # Structured table data
    extracted_metadata = Column(JSON().with_variant(__import__("sqlalchemy.dialects.postgresql", fromlist=["JSONB"]).JSONB(), "postgresql"), nullable=True)  # Document metadata (author, dates, etc.)

    # Quality metrics
    confidence_score = Column(Numeric(5, 2), nullable=True)
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    has_tables = Column(Boolean, nullable=False, default=False)
    has_images = Column(Boolean, nullable=False, default=False)

    # Processing metadata
    processing_time_seconds = Column(Numeric(10, 2), nullable=True)
    parser_version = Column(String(50), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
