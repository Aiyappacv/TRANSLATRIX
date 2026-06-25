"""
Super Admin Models
Platform administration audit logging
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class SuperAdminAuditLog(Base):
    """
    Super admin audit log
    Track all platform-level administrative actions
    """
    __tablename__ = "super_admin_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # e.g., "company_suspended", "user_created"
    resource_type = Column(String(50), nullable=True, index=True)  # e.g., "company", "user", "tenant"
    resource_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Request context
    description = Column(Text, nullable=True)
    action_metadata = Column(JSON, nullable=True)  # Additional context data
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<SuperAdminAuditLog(id={self.id}, action={self.action})>"
