"""
Tenant Schemas
Pydantic models for tenant requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class TenantStatusEnum(str, Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    TRIAL = "trial"


class TenantBase(BaseModel):
    """Base tenant schema"""
    name: str = Field(..., min_length=2, max_length=255)
    plan: Optional[str] = Field(None, max_length=50)


class TenantCreate(TenantBase):
    """Tenant creation schema"""
    status: TenantStatusEnum = TenantStatusEnum.ACTIVE


class TenantUpdate(BaseModel):
    """Tenant update schema"""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    plan: Optional[str] = Field(None, max_length=50)
    status: Optional[TenantStatusEnum] = None


class TenantResponse(TenantBase):
    """Tenant response schema"""
    id: str
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantListResponse(BaseModel):
    """Tenant list response with pagination"""
    items: list[TenantResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class TenantStatusUpdate(BaseModel):
    """Tenant status update schema"""
    status: TenantStatusEnum
