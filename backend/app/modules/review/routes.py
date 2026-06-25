"""
Review Routes
API endpoints for review workflow
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.core.response import success_response
from app.modules.review.service import ReviewService
from app.modules.review.schemas import (
    ReviewTaskCreate,
    ReviewTaskAssign,
    ReviewTaskUpdate,
    ReviewTaskCorrection,
    ReviewTaskResponse,
    ReviewTaskListResponse,
    ReviewStatistics
)

router = APIRouter()


@router.post("/review-tasks", response_model=ReviewTaskResponse)
def create_review_task(
    data: ReviewTaskCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Create a new review task
    Requires ADMIN or REVIEWER role
    """
    task = ReviewService.create_review_task(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        data=data
    )
    return ReviewTaskResponse.model_validate(task)


@router.get("/review-tasks", response_model=ReviewTaskListResponse)
def list_review_tasks(
    assigned_to: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    List review tasks with filters
    """
    skip = (page - 1) * page_size
    tasks, total = ReviewService.list_review_tasks(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        assigned_to=assigned_to,
        status=status,
        skip=skip,
        limit=page_size
    )

    return ReviewTaskListResponse(
        tasks=[ReviewTaskResponse.model_validate(task) for task in tasks],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/review-tasks/{task_id}", response_model=ReviewTaskResponse)
def get_review_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get a review task by ID"""
    task = ReviewService.get_review_task(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        task_id=task_id
    )
    return ReviewTaskResponse.model_validate(task)


@router.post("/review-tasks/{task_id}/assign", response_model=ReviewTaskResponse)
def assign_review_task(
    task_id: UUID,
    data: ReviewTaskAssign,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """
    Assign a review task to a user
    Requires ADMIN role
    """
    task = ReviewService.assign_review_task(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        task_id=task_id,
        assigned_to=data.assigned_to
    )
    return ReviewTaskResponse.model_validate(task)


@router.patch("/review-tasks/{task_id}", response_model=ReviewTaskResponse)
def update_review_task(
    task_id: UUID,
    data: ReviewTaskUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Update a review task"""
    task = ReviewService.update_review_task(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        task_id=task_id,
        data=data
    )
    return ReviewTaskResponse.model_validate(task)


@router.post("/review-tasks/{task_id}/corrections", response_model=ReviewTaskResponse)
def submit_corrections(
    task_id: UUID,
    data: ReviewTaskCorrection,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Submit corrections for a review task"""
    task = ReviewService.submit_corrections(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        task_id=task_id,
        user_id=current_user["user_id"],
        data=data
    )
    return ReviewTaskResponse.model_validate(task)


@router.post("/review-tasks/{task_id}/complete", response_model=ReviewTaskResponse)
def complete_review_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Complete a review task"""
    task = ReviewService.complete_review_task(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        task_id=task_id,
        user_id=current_user["user_id"]
    )
    return ReviewTaskResponse.model_validate(task)


@router.get("/review-tasks/statistics", response_model=ReviewStatistics)
def get_review_statistics(
    user_id: Optional[UUID] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get review statistics"""
    stats = ReviewService.get_review_statistics(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=user_id
    )
    return stats
