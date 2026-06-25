"""
Review Schemas
Request/response schemas for review workflow
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class ReviewStatusEnum(str, Enum):
    """Review task status enum"""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    CORRECTIONS_REQUESTED = "corrections_requested"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReviewTaskCreate(BaseModel):
    """Schema for creating a review task"""
    entry_id: UUID
    assigned_to: Optional[UUID] = None
    review_notes: Optional[str] = None
    confidence_flags: Optional[Dict[str, Any]] = None


class ReviewTaskAssign(BaseModel):
    """Schema for assigning a review task"""
    assigned_to: UUID


class ReviewTaskUpdate(BaseModel):
    """Schema for updating review task"""
    status: Optional[ReviewStatusEnum] = None
    review_notes: Optional[str] = None
    corrections: Optional[Dict[str, Any]] = None


class ReviewTaskCorrection(BaseModel):
    """Schema for submitting corrections"""
    corrections: Dict[str, Any] = Field(..., description="Corrections to apply to the entry")
    review_notes: Optional[str] = None


class ReviewTaskResponse(BaseModel):
    """Schema for review task response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_id: UUID
    assigned_to: Optional[UUID]
    status: ReviewStatusEnum
    review_notes: Optional[str]
    corrections: Optional[Dict[str, Any]]
    confidence_flags: Optional[Dict[str, Any]]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


class ReviewTaskListResponse(BaseModel):
    """Schema for review task list response"""
    tasks: List[ReviewTaskResponse]
    total: int
    page: int
    page_size: int


class ReviewStatistics(BaseModel):
    """Review statistics"""
    total_tasks: int
    pending: int
    in_review: int
    completed: int
    cancelled: int
    corrections_requested: int
    avg_review_time_minutes: Optional[float] = None
