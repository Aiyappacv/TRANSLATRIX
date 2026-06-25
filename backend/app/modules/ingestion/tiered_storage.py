from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

import structlog
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Session, relationship
import enum

from app.database import Base
from app.modules.storage.adapters.base import BaseStorage

logger = structlog.get_logger(__name__)


class LakeTier(str, enum.Enum):
    RAW = "raw"
    PROCESSED = "processed"
    CURATED = "curated"


class ProcessingStep(str, enum.Enum):
    UPLOADED = "uploaded"
    PREPROCESSING = "preprocessing"
    PREPROCESSED = "preprocessed"
    DEDUPLICATION = "deduplication"
    DEDUPLICATED = "deduplicated"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    VALIDATING = "validating"
    VALIDATED = "validated"
    FAILED = "failed"


class LakeRecord(Base):
    __tablename__ = "lake_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("ingested_files.id", ondelete="CASCADE"), nullable=False, index=True)
    tier = Column(SAEnum(LakeTier), nullable=False)
    storage_key = Column(String(1024), nullable=False)
    storage_url = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=False)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(Integer, nullable=False, default=0)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    file = relationship("IngestedFile", backref="lake_records")


class ProcessingAudit(Base):
    __tablename__ = "processing_audit"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("ingested_files.id", ondelete="CASCADE"), nullable=False, index=True)
    step = Column(SAEnum(ProcessingStep), nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id = Column(PG_UUID(as_uuid=True), ForeignKey("ingested_files.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    tenant_id = Column(PG_UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    embedding_dim = Column(Integer, nullable=False, default=384)
    embedding_path = Column(String(1024), nullable=False)
    model_name = Column(String(255), nullable=False, default="all-MiniLM-L6-v2")
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TieredStorageManager:
    def __init__(self, db: Session, storage: BaseStorage):
        self.db = db
        self.storage = storage

    def _tier_prefix(self, tier: LakeTier, tenant_id: str, company_id: str) -> str:
        return f"datalake/{tier.value}/tenants/{tenant_id}/companies/{company_id}"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    async def store_raw(
        self,
        file_content: bytes,
        tenant_id: UUID,
        company_id: UUID,
        file_id: UUID,
        filename: str,
        content_type: str,
        checksum: str,
        metadata: Optional[dict] = None,
    ) -> LakeRecord:
        prefix = self._tier_prefix(LakeTier.RAW, str(tenant_id), str(company_id))
        storage_key = f"{prefix}/{file_id}_{filename}"
        await self.storage.upload_file(
            file_content=file_content,
            object_key=storage_key,
            content_type=content_type,
            metadata={"tenant_id": str(tenant_id), "file_id": str(file_id), "tier": "raw", "checksum": checksum},
        )
        record = LakeRecord(
            file_id=file_id,
            tier=LakeTier.RAW,
            storage_key=storage_key,
            checksum=checksum,
            content_type=content_type,
            size_bytes=len(file_content),
            metadata_json=metadata,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("raw_tier_stored", file_id=str(file_id), storage_key=storage_key)
        return record

    async def store_processed(
        self,
        data: dict,
        tenant_id: UUID,
        company_id: UUID,
        file_id: UUID,
        filename: str,
    ) -> LakeRecord:
        file_content = json.dumps(data, default=str).encode("utf-8")
        checksum = hashlib.sha256(file_content).hexdigest()
        basename = filename.rsplit(".", 1)[0] if "." in filename else filename
        storage_key = f"{self._tier_prefix(LakeTier.PROCESSED, str(tenant_id), str(company_id))}/{file_id}_{basename}.json"
        await self.storage.upload_file(
            file_content=file_content,
            object_key=storage_key,
            content_type="application/json",
            metadata={"tenant_id": str(tenant_id), "file_id": str(file_id), "tier": "processed"},
        )
        record = LakeRecord(
            file_id=file_id,
            tier=LakeTier.PROCESSED,
            storage_key=storage_key,
            checksum=checksum,
            content_type="application/json",
            size_bytes=len(file_content),
            metadata_json={"original_filename": filename, "record_count": len(data) if isinstance(data, list) else 1},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("processed_tier_stored", file_id=str(file_id), storage_key=storage_key)
        return record

    async def store_curated(
        self,
        features: dict,
        tenant_id: UUID,
        company_id: UUID,
        file_id: UUID,
        filename: str,
    ) -> LakeRecord:
        file_content = json.dumps(features, default=str).encode("utf-8")
        checksum = hashlib.sha256(file_content).hexdigest()
        basename = filename.rsplit(".", 1)[0] if "." in filename else filename
        storage_key = f"{self._tier_prefix(LakeTier.CURATED, str(tenant_id), str(company_id))}/{file_id}_{basename}_features.json"
        await self.storage.upload_file(
            file_content=file_content,
            object_key=storage_key,
            content_type="application/json",
            metadata={"tenant_id": str(tenant_id), "file_id": str(file_id), "tier": "curated"},
        )
        record = LakeRecord(
            file_id=file_id,
            tier=LakeTier.CURATED,
            storage_key=storage_key,
            checksum=checksum,
            content_type="application/json",
            size_bytes=len(file_content),
            metadata_json={"original_filename": filename, "feature_count": len(features)},
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        logger.info("curated_tier_stored", file_id=str(file_id), storage_key=storage_key)
        return record

    async def get_tier_data(self, file_id: UUID, tier: LakeTier) -> Optional[bytes]:
        record = self.db.query(LakeRecord).filter(LakeRecord.file_id == file_id, LakeRecord.tier == tier).order_by(LakeRecord.created_at.desc()).first()
        if not record:
            return None
        return await self.storage.download_file(record.storage_key)

    def get_tier_records(self, file_id: UUID) -> list[LakeRecord]:
        return self.db.query(LakeRecord).filter(LakeRecord.file_id == file_id).order_by(LakeRecord.created_at).all()

    def log_audit(
        self,
        file_id: UUID,
        step: ProcessingStep,
        status: str,
        message: Optional[str] = None,
        duration_ms: Optional[int] = None,
        metadata_json: Optional[dict] = None,
    ) -> ProcessingAudit:
        record = ProcessingAudit(
            file_id=file_id,
            step=step,
            status=status,
            message=message,
            duration_ms=duration_ms,
            metadata_json=metadata_json,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
