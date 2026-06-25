"""
Audit Models
Comprehensive audit logging for all critical operations
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class AuditLog(Base):
    """
    Audit log for tenant-level operations
    Tracks all changes to critical business data
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Action details
    entity_type = Column(String(100), nullable=False, index=True)  # entry, company, mapping, etc.
    entity_id = Column(String(100), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # create, update, delete, approve, post
    description = Column(Text, nullable=True)

    # Change tracking
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # Request context
    request_id = Column(String(100), nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog(entity={self.entity_type}, action={self.action})>"
