"""
Audit Schemas
Request/response schemas for audit logging
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID


class AuditLogResponse(BaseModel):
    """Audit log response schema"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID]
    entity_type: str
    entity_id: str
    action: str
    description: Optional[str]
    old_value: Optional[Dict[str, Any]]
    new_value: Optional[Dict[str, Any]]
    request_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime


class AuditLogListResponse(BaseModel):
    """Audit log list response"""
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


class AuditLogQueryRequest(BaseModel):
    """Audit log query request"""
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action: Optional[str] = None
    user_id: Optional[UUID] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
