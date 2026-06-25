"""
Review and Approval Models
Human review and approval workflow
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Enum as SQLEnum, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class ReviewStatus(enum.Enum):
    """Review task status"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    CORRECTIONS_REQUESTED = "corrections_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ApprovalStatus(enum.Enum):
    """Approval status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ReviewTask(Base):
    """Review tasks for financial entries"""
    __tablename__ = "review_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    entry_id = Column(UUID(as_uuid=True), ForeignKey("financial_entries.id"), nullable=False, index=True)

    assigned_to = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    status = Column(SQLEnum(ReviewStatus), nullable=False, default=ReviewStatus.PENDING, index=True)

    # Review data
    review_notes = Column(Text, nullable=True)
    corrections = Column(JSON, nullable=True)
    confidence_flags = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
