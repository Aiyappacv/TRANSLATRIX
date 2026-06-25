"""
Notification Schemas
Request/response schemas for notifications
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class NotificationTypeEnum(str, Enum):
    """Notification type enum"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


class NotificationChannelEnum(str, Enum):
    """Notification channel enum"""
    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


class NotificationCreate(BaseModel):
    """Create notification"""
    user_id: UUID
    title: str
    message: str
    type: NotificationTypeEnum = NotificationTypeEnum.INFO
    channel: NotificationChannelEnum = NotificationChannelEnum.IN_APP
    link: Optional[str] = None


class NotificationResponse(BaseModel):
    """Notification response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID
    type: NotificationTypeEnum
    channel: NotificationChannelEnum
    title: str
    message: str
    link: Optional[str]
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Notification list response"""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
