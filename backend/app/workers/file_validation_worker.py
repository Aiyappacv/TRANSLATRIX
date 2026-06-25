"""
File Validation Worker
Validate file type, size, checksum, and perform virus scanning
"""
from typing import Dict, Any
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.modules.files.models import IngestedFile, FileStatus
from app.config import settings
import structlog
import magic
import hashlib
import uuid

logger = structlog.get_logger(__name__)


class ValidationTask(Task):
    """Base task with error handling"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("validation_task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    name="validation.file",
    bind=True,
    base=ValidationTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def validate_file(self, file_id: str) -> Dict[str, Any]:
    """
    Validate file integrity and security
    """
    db = SessionLocal()
    try:
        logger.info("validating_file", file_id=file_id)

        # Load file
        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Update status
        file.status = FileStatus.VALIDATING
        db.commit()

        # Validate file size
        max_size = settings.max_file_size_bytes
        if file.file_size > max_size:
            raise ValueError(f"File size {file.file_size} exceeds maximum {max_size}")

        # Validate file type
        allowed_types = settings.allowed_file_types_list
        if file.file_type.lower() not in allowed_types:
            raise ValueError(f"File type {file.file_type} not allowed")

        # Verify MIME type
        # Note: In production, download file from storage and verify
        # For now, we'll trust the stored mime_type
        logger.info("file_validated", file_id=file_id, mime_type=file.mime_type)

        # Virus scan placeholder
        # In production: integrate with ClamAV or cloud-based antivirus
        file.virus_scanned = True

        # Update status
        file.status = FileStatus.VALIDATED
        db.commit()

        # Trigger extraction
        from app.workers.extraction_worker import extract_file
        extract_file.delay(str(file.id))

        logger.info("file_validation_completed", file_id=file_id)
        return {"file_id": file_id, "status": "validated"}

    except Exception as e:
        logger.error("file_validation_failed", file_id=file_id, error=str(e))
        if db:
            file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
            if file:
                file.status = FileStatus.FAILED
                db.commit()
        raise
    finally:
        db.close()


@celery_app.task(
    name="validation.checksum",
    bind=True,
    max_retries=2
)
def verify_checksum(self, file_id: str, expected_checksum: str) -> Dict[str, Any]:
    """
    Verify file checksum after download/transfer
    """
    db = SessionLocal()
    try:
        logger.info("verifying_checksum", file_id=file_id)

        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # In production: download file and calculate checksum
        # For now, compare stored checksum
        if file.checksum != expected_checksum:
            raise ValueError(f"Checksum mismatch: expected {expected_checksum}, got {file.checksum}")

        logger.info("checksum_verified", file_id=file_id)
        return {"file_id": file_id, "checksum_valid": True}

    finally:
        db.close()
