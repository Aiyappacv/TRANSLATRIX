"""Validation Worker - Placeholder"""
from app.workers.celery_app import celery_app

@celery_app.task(name="validation.entry")
def validate_entry(entry_id: str):
    return {"entry_id": entry_id}
