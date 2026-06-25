"""Accounting Connector Worker - Placeholder"""
from app.workers.celery_app import celery_app

@celery_app.task(name="accounting.post")
def post_to_accounting(entry_id: str, connector_type: str):
    return {"entry_id": entry_id, "connector": connector_type}
