"""
Celery Application Configuration
Async task processing for TRANSLATRIX PRO
"""
from celery import Celery
from app.config import settings

# Create Celery app
celery_app = Celery(
    "translatrix_pro",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.ingestion_worker",
        "app.workers.file_validation_worker",
        "app.workers.ocr_worker",
        "app.workers.extraction_worker",
        "app.workers.classification_worker",
        "app.workers.sap_mapping_worker",
        "app.workers.accounting_worker",
        "app.workers.validation_worker",
        "app.workers.review_worker",
        "app.workers.sap_posting_worker",
        "app.workers.accounting_connector_worker",
        "app.workers.notification_worker",
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routes — dedicated queues so extraction and ingestion
# each have their own worker pool and one slow task type cannot starve another.
celery_app.conf.task_routes = {
    "app.workers.ingestion_worker.*": {"queue": "ingestion"},
    "app.workers.extraction_worker.*": {"queue": "extraction"},
    "app.workers.ocr_worker.*": {"queue": "ocr"},
    "app.workers.classification_worker.*": {"queue": "classification"},
    "app.workers.sap_posting_worker.*": {"queue": "posting"},
    "app.workers.validation_worker.*": {"queue": "validation"},
    "app.workers.review_worker.*": {"queue": "review"},
}
