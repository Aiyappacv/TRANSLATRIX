"""
Analytics Models
Metrics aggregation and analytics models
"""
from sqlalchemy import Column, String, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class ProcessingMetrics(Base):
    """Processing metrics aggregation"""
    __tablename__ = "processing_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    # Time period
    period_type = Column(String(20), nullable=False, index=True)  # hourly, daily, weekly, monthly
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)

    # Metrics
    files_uploaded = Column(Integer, nullable=False, default=0)
    files_processed = Column(Integer, nullable=False, default=0)
    entries_created = Column(Integer, nullable=False, default=0)
    entries_approved = Column(Integer, nullable=False, default=0)
    entries_posted = Column(Integer, nullable=False, default=0)

    # Processing times (in seconds)
    avg_ocr_time = Column(Float, nullable=True)
    avg_translation_time = Column(Float, nullable=True)
    avg_extraction_time = Column(Float, nullable=True)
    avg_total_processing_time = Column(Float, nullable=True)

    # Quality metrics
    avg_confidence_score = Column(Float, nullable=True)
    manual_review_rate = Column(Float, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
