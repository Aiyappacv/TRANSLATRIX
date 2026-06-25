"""
Notification Models
User notifications and alerts
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class NotificationType(enum.Enum):
    """Notification type"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationChannel(enum.Enum):
    """Notification delivery channel"""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class Notification(Base):
    """User notifications"""
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Notification details
    type = Column(SQLEnum(NotificationType), nullable=False, default=NotificationType.INFO)
    channel = Column(SQLEnum(NotificationChannel), nullable=False, default=NotificationChannel.IN_APP)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(500), nullable=True)

    # Status
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
