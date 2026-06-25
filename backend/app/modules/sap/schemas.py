"""
SAP Schemas
Request/response schemas for SAP integration
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID
from enum import Enum


class SAPStatusEnum(str, Enum):
    """SAP posting status enum"""
    PENDING = "pending"
    POSTING = "posting"
    POSTED = "posted"
    FAILED = "failed"


class SAPConnectionConfigCreate(BaseModel):
    """Schema for creating SAP connection configuration"""
    base_url: str = Field(..., description="SAP base URL")
    client: str = Field(..., description="SAP client number")
    username: str = Field(..., description="SAP username")
    password: str = Field(..., description="SAP password (will be encrypted)")
    environment: str = Field(default="sandbox", description="Environment: sandbox or production")


class SAPConnectionConfigUpdate(BaseModel):
    """Schema for updating SAP connection configuration"""
    base_url: Optional[str] = None
    client: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    environment: Optional[str] = None
    is_active: Optional[bool] = None


class SAPConnectionConfigResponse(BaseModel):
    """Schema for SAP connection configuration response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    base_url: str
    client: str
    username: str
    environment: str
    is_active: bool
    last_tested_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SAPConnectionTestResponse(BaseModel):
    """Schema for SAP connection test response"""
    connected: bool
    message: Optional[str] = None
    tested_at: datetime


class SAPPostingRequest(BaseModel):
    """Schema for SAP posting request"""
    entry_id: UUID
    document_type: str = Field(default="SA", description="SAP document type")
    force_repost: bool = Field(default=False, description="Force repost even if already posted")


class SAPBatchPostingRequest(BaseModel):
    """Schema for batch SAP posting request"""
    entry_ids: List[UUID] = Field(..., description="List of entry IDs to post")
    document_type: str = Field(default="SA", description="SAP document type")


class SAPPostingResultResponse(BaseModel):
    """Schema for SAP posting result response"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    entry_id: UUID
    payload_id: UUID
    status: SAPStatusEnum
    sap_document_number: Optional[str]
    fiscal_year: Optional[str]
    company_code: Optional[str]
    sap_response: Optional[Dict[str, Any]]
    error_code: Optional[str]
    error_message: Optional[str]
    posted_by: Optional[UUID]
    posted_at: Optional[datetime]
    created_at: datetime


class SAPBatchPostingResultResponse(BaseModel):
    """Schema for batch posting result"""
    total: int
    successful: int
    failed: int
    results: List[SAPPostingResultResponse]


class SAPPostingStatistics(BaseModel):
    """SAP posting statistics"""
    total_postings: int
    pending: int
    posting: int
    posted: int
    failed: int
    success_rate: float
