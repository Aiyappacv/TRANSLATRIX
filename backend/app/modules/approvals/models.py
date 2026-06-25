"""
Approval Models
Multi-level approval workflow models
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class ApprovalStatus(enum.Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalHistory(Base):
    """Approval history for financial entries"""
    __tablename__ = "approval_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False, index=True)

    approver_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(ApprovalStatus), nullable=False)
    comments = Column(Text, nullable=True)
    approval_level = Column(Integer, nullable=False, default=1)  # Support multi-level approval

    # Additional metadata
    changes_requested = Column(JSON, nullable=True)  # Specific changes requested
    approval_metadata = Column(JSON, nullable=True)  # Additional metadata

    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)
