"""
Classification Worker
Classify financial entries into categories
"""
from typing import Dict, Any
from celery import Task
from app.workers.celery_app import celery_app
from app.database import SessionLocal
from app.modules.files.models import IngestedFile, FileStatus
from app.modules.entries.models import FinancialEntry, FinancialClassification, FinancialCategory, EntryStatus
from app.modules.classification.adapters import get_classifier
from app.config import settings
import structlog
import uuid

logger = structlog.get_logger(__name__)


class ClassificationTask(Task):
    """Base task with error handling"""
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger.error("classification_task_failed", task_id=task_id, error=str(exc))


@celery_app.task(
    name="classification.classify_entries",
    bind=True,
    base=ClassificationTask,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True
)
def classify_entries(self, file_id: str) -> Dict[str, Any]:
    """
    Classify all financial entries from a file
    """
    db = SessionLocal()
    try:
        logger.info("classifying_entries", file_id=file_id)

        file = db.query(IngestedFile).filter(IngestedFile.id == uuid.UUID(file_id)).first()
        if not file:
            raise ValueError(f"File {file_id} not found")

        file.status = FileStatus.CLASSIFYING
        db.commit()

        # Get financial entries
        entries = db.query(FinancialEntry).filter(FinancialEntry.file_id == file.id).all()

        if not entries:
            logger.warning("no_entries_to_classify", file_id=file_id)
            file.status = FileStatus.CLASSIFIED
            db.commit()
            return {"file_id": file_id, "count": 0}

        # Get classifier
        classifier = get_classifier()

        classified_count = 0
        for entry in entries:
            # Classify entry
            classification_result = classifier.classify(
                description=entry.translated_description or entry.original_description,
                amount=float(entry.amount) if entry.amount else None,
                vendor=entry.vendor_name,
                reference=entry.reference_number
            )

            # Save classification
            classification = FinancialClassification(
                entry_id=entry.id,
                category=FinancialCategory[classification_result['category'].upper()],
                subcategory=classification_result.get('subcategory'),
                confidence=classification_result['confidence'],
                reason=classification_result.get('reason'),
                classification_method=classification_result.get('method', 'ai')
            )
            db.add(classification)

            # Update entry
            entry.category = classification.category
            entry.subcategory = classification.subcategory
            entry.classification_confidence = classification.confidence
            entry.status = EntryStatus.CLASSIFIED

            classified_count += 1

        file.status = FileStatus.CLASSIFIED
        db.commit()

        # Trigger SAP mapping
        from app.workers.sap_mapping_worker import map_to_sap
        map_to_sap.delay(str(file.id))

        logger.info("classification_completed", file_id=file_id, classified_count=classified_count)
        return {"file_id": file_id, "count": classified_count}

    except Exception as e:
        logger.error("classification_failed", file_id=file_id, error=str(e))
        raise
    finally:
        db.close()


@celery_app.task(
    name="classification.classify_entry",
    bind=True,
    base=ClassificationTask,
    max_retries=3
)
def classify_financial_entry(self, entry_id: str) -> Dict[str, Any]:
    """
    Classify a single financial entry
    """
    db = SessionLocal()
    try:
        logger.info("classifying_entry", entry_id=entry_id)

        entry = db.query(FinancialEntry).filter(FinancialEntry.id == uuid.UUID(entry_id)).first()
        if not entry:
            raise ValueError(f"Entry {entry_id} not found")

        classifier = get_classifier()
        classification_result = classifier.classify(
            description=entry.translated_description or entry.original_description,
            amount=float(entry.amount) if entry.amount else None,
            vendor=entry.vendor_name,
            reference=entry.reference_number
        )

        classification = FinancialClassification(
            entry_id=entry.id,
            category=FinancialCategory[classification_result['category'].upper()],
            subcategory=classification_result.get('subcategory'),
            confidence=classification_result['confidence'],
            reason=classification_result.get('reason'),
            classification_method=classification_result.get('method', 'ai')
        )
        db.add(classification)

        entry.category = classification.category
        entry.subcategory = classification.subcategory
        entry.classification_confidence = classification.confidence
        entry.status = EntryStatus.CLASSIFIED

        db.commit()

        return {"entry_id": entry_id, "category": classification.category.value}

    finally:
        db.close()
