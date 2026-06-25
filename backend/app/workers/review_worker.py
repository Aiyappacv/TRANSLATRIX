"""Review Worker - Placeholder"""
from app.workers.celery_app import celery_app

@celery_app.task(name="review.create_task")
def create_review_task(entry_id: str):
    return {"entry_id": entry_id}
