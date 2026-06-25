from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey, JSON, Enum as SAEnum, BigInteger, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class SourceChannel(str, enum.Enum):
    PORTAL = "portal"
    API = "api"
    EMAIL = "email"
    SFTP = "sftp"
    BARCODE = "barcode"
    VOICE = "voice"


class IntakeStatus(str, enum.Enum):
    """Document lifecycle status.

    The database enum values are uppercase (historical migration); make the
    Python enum values match the stored enum labels so SQLAlchemy can round-trip
    values without type errors when inserting/updating registry rows.
    """
    UPLOADING = "UPLOADING"
    UPLOADED = "UPLOADED"
    METADATA_PROCESSING = "METADATA_PROCESSING"
    METADATA_READY = "METADATA_READY"
    READY_FOR_EXTRACTION = "READY_FOR_EXTRACTION"
    EXTRACTING = "EXTRACTING"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"


class IntakeRegistry(Base):
    __tablename__ = "intake_registry"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    file_id = Column(UUID(as_uuid=True), ForeignKey("ingested_files.id", ondelete="SET NULL"), nullable=True, index=True)

    original_filename = Column(String(512), nullable=False)
    source_channel = Column(SAEnum(SourceChannel), nullable=False, default=SourceChannel.PORTAL)
    document_type = Column(String(100), nullable=True)
    language = Column(String(10), nullable=True)
    status = Column(SAEnum(IntakeStatus), nullable=False, default=IntakeStatus.UPLOADING, index=True)

    tier = Column(String(50), nullable=True)
    is_duplicate = Column(Boolean, nullable=False, default=False)
    duplicate_of_id = Column(UUID(as_uuid=True), ForeignKey("intake_registry.id", ondelete="SET NULL"), nullable=True, index=True)
    duplicate_similarity = Column(Float, nullable=True)
    # Populated by the background metadata worker, not at upload time —
    # computing this synchronously was the single biggest contributor to
    # slow bulk uploads (hashing N large files before the request can return).
    checksum = Column(String(64), nullable=True, index=True)

    file_size = Column(BigInteger, nullable=False, default=0)
    mime_type = Column(String(100), nullable=True)
    page_count = Column(Integer, nullable=True)
    language_detected = Column(String(10), nullable=True)
    orientation = Column(String(20), nullable=True)

    processing_metadata = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    file = relationship("IngestedFile", backref="intake_registry", lazy="select")
    duplicate_of = relationship("IntakeRegistry", remote_side="IntakeRegistry.id", backref="duplicates", lazy="select")


class IntakeEvent(Base):
    __tablename__ = "intake_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    registry_id = Column(UUID(as_uuid=True), ForeignKey("intake_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    registry = relationship("IntakeRegistry", backref="events")
