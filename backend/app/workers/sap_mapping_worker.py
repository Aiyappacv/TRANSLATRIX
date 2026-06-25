"""SAP Mapping Worker - Placeholder"""
from app.workers.celery_app import celery_app

@celery_app.task(name="sap.map")
def map_to_sap(entry_id: str):
    return {"entry_id": entry_id}
