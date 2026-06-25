"""
Notification Service
Business logic for notifications
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.modules.notifications.models import Notification, NotificationType, NotificationChannel
from app.exceptions import NotFoundError

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for managing notifications"""

    @staticmethod
    def create_notification(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: NotificationType = NotificationType.INFO,
        channel: NotificationChannel = NotificationChannel.IN_APP,
        link: Optional[str] = None
    ) -> Notification:
        """Create a notification"""
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            type=notification_type,
            channel=channel,
            title=title,
            message=message,
            link=link
        )

        db.add(notification)
        db.commit()
        db.refresh(notification)

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            user_id=str(user_id),
            type=notification_type.value
        )

        # Send via channel (email, webhook, etc.)
        NotificationService._send_notification(notification)

        return notification

    @staticmethod
    def get_user_notifications(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Notification], int]:
        """Get user notifications"""
        query = db.query(Notification).filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id
            )
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()
        notifications = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

        return notifications, total

    @staticmethod
    def mark_as_read(
        db: Session,
        tenant_id: UUID,
        user_id: UUID,
        notification_id: UUID
    ) -> Notification:
        """Mark notification as read"""
        notification = db.query(Notification).filter(
            and_(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id
            )
        ).first()

        if not notification:
            raise NotFoundError(f"Notification {notification_id} not found")

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        db.commit()
        db.refresh(notification)

        return notification

    @staticmethod
    def mark_all_as_read(
        db: Session,
        tenant_id: UUID,
        user_id: UUID
    ) -> int:
        """Mark all notifications as read"""
        count = db.query(Notification).filter(
            and_(
                Notification.tenant_id == tenant_id,
                Notification.user_id == user_id,
                Notification.is_read == False
            )
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })

        db.commit()

        logger.info("marked_all_notifications_read", user_id=str(user_id), count=count)

        return count

    @staticmethod
    def _send_notification(notification: Notification) -> None:
        """Send notification via appropriate channel"""
        if notification.channel == NotificationChannel.EMAIL:
            # Email sending logic (placeholder)
            logger.info("sending_email_notification", notification_id=str(notification.id))
            # In production: Send actual email

        elif notification.channel == NotificationChannel.WEBHOOK:
            # Webhook posting logic (placeholder)
            logger.info("sending_webhook_notification", notification_id=str(notification.id))
            # In production: Post to webhook

        # IN_APP notifications don't need sending - they're stored in DB
