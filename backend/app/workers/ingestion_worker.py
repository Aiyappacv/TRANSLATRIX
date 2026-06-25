"""
Ingestion Worker
Process file ingestion from shared links and cloud storage
"""
from typing import Dict, Any
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.modules.files.models import IngestionBatch, IngestedFile, BatchStatus, FileStatus
from app.modules.ingestion.connectors import get_connector
import structlog
import hashlib
import uuid

logger = structlog.get_logger(__name__)


class IngestionTask(Task):
    """Base task with database session"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    name="ingestion.process_batch",
    bind=True,
    base=IngestionTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True
)
def process_ingestion_batch(self, batch_id: str) -> Dict[str, Any]:
    """
    Process an ingestion batch
    Downloads files from shared links and creates file records
    """
    db = SessionLocal()
    try:
        logger.info("processing_batch", batch_id=batch_id)

        # Load batch
        batch = db.query(IngestionBatch).filter(IngestionBatch.id == uuid.UUID(batch_id)).first()
        if not batch:
            raise ValueError(f"Batch {batch_id} not found")

        # Update status
        batch.status = BatchStatus.PROCESSING
        db.commit()

        # Get connector based on source
        if batch.source_id:
            connector = get_connector(db, batch.source_id)
            files = connector.list_files()

            for file_info in files:
                # Download file
                file_data = connector.download_file(file_info['path'])

                # Calculate checksum
                checksum = hashlib.sha256(file_data).hexdigest()

                # Check for duplicates
                existing = db.query(IngestedFile).filter(
                    IngestedFile.checksum == checksum,
                    IngestedFile.tenant_id == batch.tenant_id
                ).first()

                if existing:
                    logger.info("duplicate_file_skipped", filename=file_info['name'], checksum=checksum)
                    continue

                # Create file record
                ingested_file = IngestedFile(
                    tenant_id=batch.tenant_id,
                    batch_id=batch.id,
                    original_filename=file_info['name'],
                    file_type=file_info.get('extension', ''),
                    file_size=file_info['size'],
                    checksum=checksum,
                    mime_type=file_info.get('mime_type'),
                    storage_path=file_info['path'],
                    status=FileStatus.UPLOADED
                )
                db.add(ingested_file)
                batch.total_files += 1

                # Trigger validation
                from app.workers.file_validation_worker import validate_file
                validate_file.delay(str(ingested_file.id))

        batch.status = BatchStatus.COMPLETED
        db.commit()

        logger.info("batch_completed", batch_id=batch_id, total_files=batch.total_files)
        return {"batch_id": batch_id, "status": "completed", "total_files": batch.total_files}

    except Exception as e:
        logger.error("batch_processing_failed", batch_id=batch_id, error=str(e))
        if db:
            batch = db.query(IngestionBatch).filter(IngestionBatch.id == uuid.UUID(batch_id)).first()
            if batch:
                batch.status = BatchStatus.FAILED
                db.commit()
        raise
    finally:
        db.close()


@celery_app.task(
    name="ingestion.discover_files",
    bind=True,
    base=IngestionTask,
    max_retries=3
)
def discover_files(self, source_id: str) -> Dict[str, Any]:
    """
    Discover new files from a shared link source
    """
    db = SessionLocal()
    try:
        logger.info("discovering_files", source_id=source_id)

        connector = get_connector(db, source_id)
        files = connector.list_files()

        logger.info("files_discovered", source_id=source_id, count=len(files))
        return {"source_id": source_id, "file_count": len(files), "files": files}

    finally:
        db.close()
