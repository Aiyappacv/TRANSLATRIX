"""
Notification Routes
API endpoints for notifications
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.modules.notifications.service import NotificationService
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationListResponse
)
from app.modules.notifications.models import NotificationType, NotificationChannel

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get user notifications"""
    skip = (page - 1) * page_size

    notifications, total = NotificationService.get_user_notifications(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=current_user["user_id"],
        unread_only=unread_only,
        skip=skip,
        limit=page_size
    )

    # Get unread count
    _, unread_count = NotificationService.get_user_notifications(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=current_user["user_id"],
        unread_only=True,
        skip=0,
        limit=1
    )

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Mark notification as read"""
    notification = NotificationService.mark_as_read(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=current_user["user_id"],
        notification_id=notification_id
    )
    return NotificationResponse.model_validate(notification)


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Mark all notifications as read"""
    count = NotificationService.mark_all_as_read(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=current_user["user_id"]
    )

    return {"marked_read": count}
