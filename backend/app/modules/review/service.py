"""
Review Service
Business logic for review task management
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
import structlog

from app.modules.review.models import ReviewTask, ReviewStatus
from app.modules.review.schemas import (
    ReviewTaskCreate,
    ReviewTaskUpdate,
    ReviewTaskCorrection,
    ReviewStatistics
)
from app.modules.entries.models import FinancialEntry
from app.exceptions import NotFoundError, ValidationError, PermissionError

logger = structlog.get_logger(__name__)


class ReviewService:
    """Service for managing review tasks"""

    @staticmethod
    def create_review_task(
        db: Session,
        tenant_id: UUID,
        data: ReviewTaskCreate
    ) -> ReviewTask:
        """Create a new review task"""
        # Verify entry exists and belongs to tenant
        entry = db.query(FinancialEntry).filter(
            and_(
                FinancialEntry.id == data.entry_id,
                FinancialEntry.tenant_id == tenant_id
            )
        ).first()

        if not entry:
            raise NotFoundError(f"Financial entry {data.entry_id} not found")

        # Check if review task already exists
        existing_task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.entry_id == data.entry_id,
                ReviewTask.status.in_([ReviewStatus.PENDING, ReviewStatus.IN_REVIEW])
            )
        ).first()

        if existing_task:
            raise ValidationError(f"Active review task already exists for entry {data.entry_id}")

        # Create review task
        review_task = ReviewTask(
            tenant_id=tenant_id,
            entry_id=data.entry_id,
            assigned_to=data.assigned_to,
            review_notes=data.review_notes,
            confidence_flags=data.confidence_flags,
            status=ReviewStatus.PENDING
        )

        db.add(review_task)
        db.commit()
        db.refresh(review_task)

        logger.info(
            "review_task_created",
            task_id=str(review_task.id),
            entry_id=str(data.entry_id),
            tenant_id=str(tenant_id)
        )

        return review_task

    @staticmethod
    def assign_review_task(
        db: Session,
        tenant_id: UUID,
        task_id: UUID,
        assigned_to: UUID
    ) -> ReviewTask:
        """Assign a review task to a user"""
        task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.id == task_id,
                ReviewTask.tenant_id == tenant_id
            )
        ).first()

        if not task:
            raise NotFoundError(f"Review task {task_id} not found")

        if task.status not in [ReviewStatus.PENDING, ReviewStatus.IN_REVIEW]:
            raise ValidationError(f"Cannot assign task in status {task.status.value}")

        task.assigned_to = assigned_to
        if task.status == ReviewStatus.PENDING:
            task.status = ReviewStatus.IN_REVIEW
            task.started_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        logger.info(
            "review_task_assigned",
            task_id=str(task_id),
            assigned_to=str(assigned_to),
            tenant_id=str(tenant_id)
        )

        return task

    @staticmethod
    def update_review_task(
        db: Session,
        tenant_id: UUID,
        task_id: UUID,
        data: ReviewTaskUpdate
    ) -> ReviewTask:
        """Update a review task"""
        task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.id == task_id,
                ReviewTask.tenant_id == tenant_id
            )
        ).first()

        if not task:
            raise NotFoundError(f"Review task {task_id} not found")

        # Update fields
        if data.status is not None:
            task.status = ReviewStatus[data.status.value.upper()]
            if data.status.value == "in_review" and not task.started_at:
                task.started_at = datetime.utcnow()
            elif data.status.value == "completed":
                task.completed_at = datetime.utcnow()

        if data.review_notes is not None:
            task.review_notes = data.review_notes

        if data.corrections is not None:
            task.corrections = data.corrections

        db.commit()
        db.refresh(task)

        logger.info(
            "review_task_updated",
            task_id=str(task_id),
            status=task.status.value,
            tenant_id=str(tenant_id)
        )

        return task

    @staticmethod
    def submit_corrections(
        db: Session,
        tenant_id: UUID,
        task_id: UUID,
        user_id: UUID,
        data: ReviewTaskCorrection
    ) -> ReviewTask:
        """Submit corrections for a review task"""
        task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.id == task_id,
                ReviewTask.tenant_id == tenant_id
            )
        ).first()

        if not task:
            raise NotFoundError(f"Review task {task_id} not found")

        # Verify user is assigned to this task
        if task.assigned_to != user_id:
            raise PermissionError("You are not assigned to this review task")

        # Update task with corrections
        task.corrections = data.corrections
        task.review_notes = data.review_notes or task.review_notes
        task.status = ReviewStatus.CORRECTIONS_REQUESTED

        db.commit()
        db.refresh(task)

        logger.info(
            "review_corrections_submitted",
            task_id=str(task_id),
            user_id=str(user_id),
            tenant_id=str(tenant_id)
        )

        return task

    @staticmethod
    def complete_review_task(
        db: Session,
        tenant_id: UUID,
        task_id: UUID,
        user_id: UUID
    ) -> ReviewTask:
        """Complete a review task"""
        task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.id == task_id,
                ReviewTask.tenant_id == tenant_id
            )
        ).first()

        if not task:
            raise NotFoundError(f"Review task {task_id} not found")

        # Verify user is assigned to this task
        if task.assigned_to != user_id:
            raise PermissionError("You are not assigned to this review task")

        task.status = ReviewStatus.COMPLETED
        task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        logger.info(
            "review_task_completed",
            task_id=str(task_id),
            user_id=str(user_id),
            tenant_id=str(tenant_id)
        )

        return task

    @staticmethod
    def get_review_task(
        db: Session,
        tenant_id: UUID,
        task_id: UUID
    ) -> ReviewTask:
        """Get a review task by ID"""
        task = db.query(ReviewTask).filter(
            and_(
                ReviewTask.id == task_id,
                ReviewTask.tenant_id == tenant_id
            )
        ).first()

        if not task:
            raise NotFoundError(f"Review task {task_id} not found")

        return task

    @staticmethod
    def list_review_tasks(
        db: Session,
        tenant_id: UUID,
        assigned_to: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ReviewTask], int]:
        """List review tasks with filters"""
        query = db.query(ReviewTask).filter(ReviewTask.tenant_id == tenant_id)

        # Apply filters
        if assigned_to:
            query = query.filter(ReviewTask.assigned_to == assigned_to)

        if status:
            query = query.filter(ReviewTask.status == ReviewStatus[status.upper()])

        # Get total count
        total = query.count()

        # Apply pagination
        tasks = query.order_by(ReviewTask.created_at.desc()).offset(skip).limit(limit).all()

        return tasks, total

    @staticmethod
    def get_review_statistics(
        db: Session,
        tenant_id: UUID,
        user_id: Optional[UUID] = None
    ) -> ReviewStatistics:
        """Get review task statistics"""
        query = db.query(ReviewTask).filter(ReviewTask.tenant_id == tenant_id)

        if user_id:
            query = query.filter(ReviewTask.assigned_to == user_id)

        total_tasks = query.count()

        # Status counts
        pending = query.filter(ReviewTask.status == ReviewStatus.PENDING).count()
        in_review = query.filter(ReviewTask.status == ReviewStatus.IN_REVIEW).count()
        completed = query.filter(ReviewTask.status == ReviewStatus.COMPLETED).count()
        cancelled = query.filter(ReviewTask.status == ReviewStatus.CANCELLED).count()
        corrections_requested = query.filter(
            ReviewTask.status == ReviewStatus.CORRECTIONS_REQUESTED
        ).count()

        # Calculate average review time for completed tasks
        completed_tasks = query.filter(
            and_(
                ReviewTask.status == ReviewStatus.COMPLETED,
                ReviewTask.started_at.isnot(None),
                ReviewTask.completed_at.isnot(None)
            )
        ).all()

        avg_review_time = None
        if completed_tasks:
            total_minutes = sum([
                (task.completed_at - task.started_at).total_seconds() / 60
                for task in completed_tasks
            ])
            avg_review_time = total_minutes / len(completed_tasks)

        return ReviewStatistics(
            total_tasks=total_tasks,
            pending=pending,
            in_review=in_review,
            completed=completed,
            cancelled=cancelled,
            corrections_requested=corrections_requested,
            avg_review_time_minutes=avg_review_time
        )
