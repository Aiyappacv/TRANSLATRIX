"""Notification Worker - Placeholder"""
from app.workers.celery_app import celery_app

@celery_app.task(name="notification.send")
def send_notification(user_id: str, message: str):
    return {"user_id": user_id, "sent": True}
