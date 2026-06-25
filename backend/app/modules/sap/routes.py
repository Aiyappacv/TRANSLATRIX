"""
SAP Routes
API endpoints for SAP S/4HANA integration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.core.response import success_response
from app.modules.sap.service import SAPService
from app.modules.sap.schemas import (
    SAPConnectionConfigCreate,
    SAPConnectionConfigUpdate,
    SAPConnectionConfigResponse,
    SAPConnectionTestResponse,
    SAPPostingRequest,
    SAPBatchPostingRequest,
    SAPPostingResultResponse,
    SAPBatchPostingResultResponse,
    SAPPostingStatistics
)

router = APIRouter()


@router.post("/config", response_model=SAPConnectionConfigResponse)
def create_sap_config(
    data: SAPConnectionConfigCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Configure SAP connection
    Requires ADMIN role
    """
    config = SAPService.create_sap_config(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        data=data
    )
    return SAPConnectionConfigResponse.model_validate(config)


@router.put("/config", response_model=SAPConnectionConfigResponse)
def update_sap_config(
    data: SAPConnectionConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Update SAP connection configuration
    Requires ADMIN role
    """
    config = SAPService.update_sap_config(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        data=data
    )
    return SAPConnectionConfigResponse.model_validate(config)


@router.get("/config", response_model=SAPConnectionConfigResponse)
def get_sap_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get SAP connection configuration"""
    config = SAPService.get_sap_config(
        db=db,
        tenant_id=tenant_context["tenant_id"]
    )
    return SAPConnectionConfigResponse.model_validate(config)


@router.post("/test-connection", response_model=SAPConnectionTestResponse)
def test_sap_connection(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Test SAP connection
    Requires ADMIN role
    """
    is_connected, error_message = SAPService.test_sap_connection(
        db=db,
        tenant_id=tenant_context["tenant_id"]
    )

    return SAPConnectionTestResponse(
        connected=is_connected,
        message=error_message,
        tested_at=datetime.utcnow()
    )


@router.post("/entries/{entry_id}/post", response_model=SAPPostingResultResponse)
def post_entry_to_sap(
    entry_id: UUID,
    request: Optional[SAPPostingRequest] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Post financial entry to SAP
    Requires APPROVER role
    """
    document_type = request.document_type if request else "SA"
    force_repost = request.force_repost if request else False

    result = SAPService.post_entry_to_sap(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_id=entry_id,
        user_id=current_user["user_id"],
        document_type=document_type,
        force_repost=force_repost
    )

    return SAPPostingResultResponse.model_validate(result)


@router.post("/entries/batch-post", response_model=SAPBatchPostingResultResponse)
def batch_post_entries(
    request: SAPBatchPostingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Batch post multiple entries to SAP
    Requires APPROVER role
    """
    results = SAPService.batch_post_entries(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_ids=request.entry_ids,
        user_id=current_user["user_id"],
        document_type=request.document_type
    )

    return SAPBatchPostingResultResponse(
        total=results["total"],
        successful=results["successful"],
        failed=results["failed"],
        results=[SAPPostingResultResponse.model_validate(r) for r in results["results"]]
    )


@router.get("/posting-results/{result_id}", response_model=SAPPostingResultResponse)
def get_posting_result(
    result_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get SAP posting result"""
    result = SAPService.get_posting_result(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        result_id=result_id
    )
    return SAPPostingResultResponse.model_validate(result)


@router.get("/statistics", response_model=SAPPostingStatistics)
def get_sap_statistics(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get SAP posting statistics"""
    stats = SAPService.get_posting_statistics(
        db=db,
        tenant_id=tenant_context["tenant_id"]
    )
    return stats
