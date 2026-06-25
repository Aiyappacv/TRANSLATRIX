"""
OCR Worker
Process optical character recognition with Mistral OCR (primary) and configured fallbacks.
"""
from typing import Dict, Any, List
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.modules.files.models import IngestedFile, FileStatus
from app.modules.ocr.models import OCRResult
from app.modules.ocr.adapters import get_ocr_adapter
from app.config import settings
import structlog
import uuid

logger = structlog.get_logger(__name__)


class OCRTask(Task):
    """Base task with error handling"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("ocr_task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    name="ocr.process_file",
    bind=True,
    base=OCRTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    time_limit=600
)
def process_file_ocr(self, file_id: str) -> Dict[str, Any]:
    """
    Process file with OCR
    Uses PaddleOCR for primary OCR, cloud fallback if confidence is low
    """
    db = SessionLocal()
    try:
        logger.info("processing_ocr", file_id=file_id)

        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        # Get OCR adapter
        ocr_adapter = get_ocr_adapter(settings.OCR_PRIMARY_PROVIDER)
        file_path = file.storage_path

        # Process OCR
        ocr_results = ocr_adapter.process(file_path)

        # Save OCR results
        total_blocks = 0
        for page_num, page_result in enumerate(ocr_results.get('pages', []), start=1):
            for block in page_result.get('blocks', []):
                ocr_result = OCRResult(
                    tenant_id=file.tenant_id,
                    file_id=file.id,
                    page_number=page_num,
                    text=block.get('text', ''),
                    confidence=block.get('confidence', 0.0),
                    bbox=block.get('bbox'),
                    language=block.get('language', 'en'),
                    provider=settings.OCR_PRIMARY_PROVIDER
                )
                db.add(ocr_result)
                total_blocks += 1

        db.commit()

        logger.info("ocr_completed", file_id=file_id, total_blocks=total_blocks)
        return {"file_id": file_id, "ocr_completed": True, "blocks": total_blocks}

    except Exception as e:
        logger.error("ocr_failed", file_id=file_id, error=str(e))
        raise
    finally:
        db.close()
