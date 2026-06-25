"""
Audit Routes
API endpoints for audit log querying
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.modules.audit.service import AuditService
from app.modules.audit.schemas import (
    AuditLogResponse,
    AuditLogListResponse
)

router = APIRouter()


@router.get("/logs", response_model=AuditLogListResponse)
def query_audit_logs(
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Query audit logs with filters
    Requires ADMIN role
    """
    skip = (page - 1) * page_size

    logs, total = AuditService.query_audit_logs(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=page_size
    )

    return AuditLogListResponse(
        logs=[AuditLogResponse.model_validate(log) for log in logs],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/logs/entity/{entity_type}/{entity_id}", response_model=List[AuditLogResponse])
def get_entity_history(
    entity_type: str,
    entity_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get complete audit history for an entity"""
    logs = AuditService.get_entity_history(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entity_type=entity_type,
        entity_id=entity_id
    )

    return [AuditLogResponse.model_validate(log) for log in logs]
