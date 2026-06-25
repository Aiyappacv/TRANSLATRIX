"""
Approval Routes
API endpoints for approval workflow
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.core.response import success_response
from app.modules.approvals.service import ApprovalService
from app.modules.approvals.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalHistoryResponse,
    ApprovalHistoryListResponse,
    ApprovalStatistics
)

router = APIRouter()


@router.post("/approvals", response_model=ApprovalHistoryResponse)
def create_approval_request(
    data: ApprovalCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Create a new approval request
    Requires ADMIN role
    """
    approval = ApprovalService.create_approval_request(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        approver_id=current_user["user_id"],
        data=data
    )
    return ApprovalHistoryResponse.model_validate(approval)


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalHistoryResponse)
def make_approval_decision(
    approval_id: UUID,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Make an approval decision (approve/reject/request changes)
    Requires APPROVER role
    """
    approval = ApprovalService.make_approval_decision(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        approval_id=approval_id,
        approver_id=current_user["user_id"],
        decision=decision
    )
    return ApprovalHistoryResponse.model_validate(approval)


@router.post("/entries/{entry_id}/approve", response_model=ApprovalHistoryResponse)
def approve_entry(
    entry_id: UUID,
    comments: Optional[str] = None,
    approval_level: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Quick approve an entry
    Requires APPROVER role
    """
    approval = ApprovalService.approve_entry(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_id=entry_id,
        approver_id=current_user["user_id"],
        comments=comments,
        approval_level=approval_level
    )
    return ApprovalHistoryResponse.model_validate(approval)


@router.post("/entries/{entry_id}/reject", response_model=ApprovalHistoryResponse)
def reject_entry(
    entry_id: UUID,
    comments: str,
    approval_level: int = Query(1, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Reject an entry
    Requires APPROVER role
    """
    approval = ApprovalService.reject_entry(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_id=entry_id,
        approver_id=current_user["user_id"],
        comments=comments,
        approval_level=approval_level
    )
    return ApprovalHistoryResponse.model_validate(approval)


@router.get("/approvals/{approval_id}", response_model=ApprovalHistoryResponse)
def get_approval_history(
    approval_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get approval history by ID"""
    approval = ApprovalService.get_approval_history(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        approval_id=approval_id
    )
    return ApprovalHistoryResponse.model_validate(approval)


@router.get("/entries/{entry_id}/approvals", response_model=ApprovalHistoryListResponse)
def list_entry_approvals(
    entry_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """List all approvals for an entry"""
    approvals = ApprovalService.list_entry_approvals(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_id=entry_id
    )
    return ApprovalHistoryListResponse(
        approvals=[ApprovalHistoryResponse.model_validate(a) for a in approvals],
        total=len(approvals)
    )


@router.get("/approvals/pending", response_model=ApprovalHistoryListResponse)
def list_pending_approvals(
    approver_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """List pending approvals"""
    skip = (page - 1) * page_size
    approvals, total = ApprovalService.list_pending_approvals(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        approver_id=approver_id,
        skip=skip,
        limit=page_size
    )
    return ApprovalHistoryListResponse(
        approvals=[ApprovalHistoryResponse.model_validate(a) for a in approvals],
        total=total
    )


@router.get("/approvals/statistics", response_model=ApprovalStatistics)
def get_approval_statistics(
    approver_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get approval statistics"""
    stats = ApprovalService.get_approval_statistics(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        approver_id=approver_id
    )
    return stats
