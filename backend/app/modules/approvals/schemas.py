"""
Approval Schemas
Request/response schemas for approval workflow
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ApprovalStatusEnum(str, Enum):
    """Approval status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class ApprovalCreate(BaseModel):
    """Schema for creating an approval request"""
    entry_id: UUID
    approval_level: int = Field(default=1, ge=1, le=10)
    comments: Optional[str] = None


class ApprovalDecision(BaseModel):
    """Schema for approval decision"""
    status: ApprovalStatusEnum
    comments: Optional[str] = None
    changes_requested: Optional[Dict[str, Any]] = None


class ApprovalHistoryResponse(BaseModel):
    """Schema for approval history response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_id: UUID
    approver_id: UUID
    status: ApprovalStatusEnum
    comments: Optional[str]
    approval_level: int
    changes_requested: Optional[Dict[str, Any]]
    approval_metadata: Optional[Dict[str, Any]]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]


class ApprovalHistoryListResponse(BaseModel):
    """Schema for approval history list response"""
    approvals: List[ApprovalHistoryResponse]
    total: int


class ApprovalStatistics(BaseModel):
    """Approval statistics"""
    total_approvals: int
    pending: int
    approved: int
    rejected: int
    changes_requested: int
    avg_approval_time_hours: Optional[float] = None
