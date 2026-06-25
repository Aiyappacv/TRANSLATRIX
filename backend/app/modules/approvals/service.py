"""
Approval Service
Business logic for approval workflow
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import structlog

from app.modules.approvals.models import ApprovalHistory, ApprovalStatus
from app.modules.approvals.schemas import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalStatistics
)
from app.modules.entries.models import FinancialEntry
from app.exceptions import NotFoundError, ValidationError, PermissionError

logger = structlog.get_logger(__name__)


class ApprovalService:
    """Service for managing approvals"""

    @staticmethod
    def create_approval_request(
        db: Session,
        tenant_id: UUID,
        approver_id: UUID,
        data: ApprovalCreate
    ) -> ApprovalHistory:
        """Create a new approval request"""
        # Verify entry exists and belongs to tenant
        entry = db.query(FinancialEntry).filter(
            and_(
                FinancialEntry.id == data.entry_id,
                FinancialEntry.tenant_id == tenant_id
            )
        ).first()

        if not entry:
            raise NotFoundError(f"Financial entry {data.entry_id} not found")

        # Check if pending approval already exists at this level
        existing_approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.entry_id == data.entry_id,
                ApprovalHistory.approval_level == data.approval_level,
                ApprovalHistory.status == ApprovalStatus.PENDING
            )
        ).first()

        if existing_approval:
            raise ValidationError(
                f"Pending approval already exists for entry {data.entry_id} at level {data.approval_level}"
            )

        # Create approval record
        approval = ApprovalHistory(
            tenant_id=tenant_id,
            entry_id=data.entry_id,
            approver_id=approver_id,
            approval_level=data.approval_level,
            status=ApprovalStatus.PENDING,
            comments=data.comments
        )

        db.add(approval)
        db.commit()
        db.refresh(approval)

        logger.info(
            "approval_request_created",
            approval_id=str(approval.id),
            entry_id=str(data.entry_id),
            approver_id=str(approver_id),
            level=data.approval_level,
            tenant_id=str(tenant_id)
        )

        return approval

    @staticmethod
    def make_approval_decision(
        db: Session,
        tenant_id: UUID,
        approval_id: UUID,
        approver_id: UUID,
        decision: ApprovalDecision
    ) -> ApprovalHistory:
        """Make an approval decision (approve/reject/request changes)"""
        approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.id == approval_id,
                ApprovalHistory.tenant_id == tenant_id
            )
        ).first()

        if not approval:
            raise NotFoundError(f"Approval {approval_id} not found")

        # Verify this user is the assigned approver
        if approval.approver_id != approver_id:
            raise PermissionError("You are not authorized to make this approval decision")

        # Check if already decided
        if approval.status != ApprovalStatus.PENDING:
            raise ValidationError(f"Approval already decided with status: {approval.status.value}")

        # Update approval
        approval.status = ApprovalStatus[decision.status.value.upper()]
        approval.comments = decision.comments or approval.comments
        approval.changes_requested = decision.changes_requested

        if decision.status == ApprovalStatusEnum.APPROVED:
            approval.approved_at = datetime.utcnow()

        db.commit()
        db.refresh(approval)

        logger.info(
            "approval_decision_made",
            approval_id=str(approval_id),
            decision=decision.status.value,
            approver_id=str(approver_id),
            tenant_id=str(tenant_id)
        )

        return approval

    @staticmethod
    def approve_entry(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID,
        approver_id: UUID,
        comments: Optional[str] = None,
        approval_level: int = 1
    ) -> ApprovalHistory:
        """Quick approve an entry"""
        decision = ApprovalDecision(
            status=ApprovalStatusEnum.APPROVED,
            comments=comments
        )

        # Create or get existing approval
        approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.entry_id == entry_id,
                ApprovalHistory.approver_id == approver_id,
                ApprovalHistory.approval_level == approval_level,
                ApprovalHistory.status == ApprovalStatus.PENDING
            )
        ).first()

        if not approval:
            # Create new approval
            create_data = ApprovalCreate(
                entry_id=entry_id,
                approval_level=approval_level,
                comments=comments
            )
            approval = ApprovalService.create_approval_request(
                db, tenant_id, approver_id, create_data
            )

        # Make decision
        return ApprovalService.make_approval_decision(
            db, tenant_id, approval.id, approver_id, decision
        )

    @staticmethod
    def reject_entry(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID,
        approver_id: UUID,
        comments: str,
        approval_level: int = 1
    ) -> ApprovalHistory:
        """Reject an entry"""
        decision = ApprovalDecision(
            status=ApprovalStatusEnum.REJECTED,
            comments=comments
        )

        # Create or get existing approval
        approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.entry_id == entry_id,
                ApprovalHistory.approver_id == approver_id,
                ApprovalHistory.approval_level == approval_level,
                ApprovalHistory.status == ApprovalStatus.PENDING
            )
        ).first()

        if not approval:
            create_data = ApprovalCreate(
                entry_id=entry_id,
                approval_level=approval_level,
                comments=comments
            )
            approval = ApprovalService.create_approval_request(
                db, tenant_id, approver_id, create_data
            )

        return ApprovalService.make_approval_decision(
            db, tenant_id, approval.id, approver_id, decision
        )

    @staticmethod
    def request_changes(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID,
        approver_id: UUID,
        comments: str,
        changes_requested: dict,
        approval_level: int = 1
    ) -> ApprovalHistory:
        """Request changes to an entry"""
        decision = ApprovalDecision(
            status=ApprovalStatusEnum.CHANGES_REQUESTED,
            comments=comments,
            changes_requested=changes_requested
        )

        # Create or get existing approval
        approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.entry_id == entry_id,
                ApprovalHistory.approver_id == approver_id,
                ApprovalHistory.approval_level == approval_level,
                ApprovalHistory.status == ApprovalStatus.PENDING
            )
        ).first()

        if not approval:
            create_data = ApprovalCreate(
                entry_id=entry_id,
                approval_level=approval_level,
                comments=comments
            )
            approval = ApprovalService.create_approval_request(
                db, tenant_id, approver_id, create_data
            )

        return ApprovalService.make_approval_decision(
            db, tenant_id, approval.id, approver_id, decision
        )

    @staticmethod
    def get_approval_history(
        db: Session,
        tenant_id: UUID,
        approval_id: UUID
    ) -> ApprovalHistory:
        """Get approval history by ID"""
        approval = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.id == approval_id,
                ApprovalHistory.tenant_id == tenant_id
            )
        ).first()

        if not approval:
            raise NotFoundError(f"Approval {approval_id} not found")

        return approval

    @staticmethod
    def list_entry_approvals(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID
    ) -> List[ApprovalHistory]:
        """List all approvals for an entry"""
        approvals = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.entry_id == entry_id,
                ApprovalHistory.tenant_id == tenant_id
            )
        ).order_by(ApprovalHistory.approval_level, ApprovalHistory.created_at).all()

        return approvals

    @staticmethod
    def list_pending_approvals(
        db: Session,
        tenant_id: UUID,
        approver_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[ApprovalHistory], int]:
        """List pending approvals"""
        query = db.query(ApprovalHistory).filter(
            and_(
                ApprovalHistory.tenant_id == tenant_id,
                ApprovalHistory.status == ApprovalStatus.PENDING
            )
        )

        if approver_id:
            query = query.filter(ApprovalHistory.approver_id == approver_id)

        total = query.count()
        approvals = query.order_by(ApprovalHistory.created_at).offset(skip).limit(limit).all()

        return approvals, total

    @staticmethod
    def get_approval_statistics(
        db: Session,
        tenant_id: UUID,
        approver_id: Optional[UUID] = None
    ) -> ApprovalStatistics:
        """Get approval statistics"""
        query = db.query(ApprovalHistory).filter(ApprovalHistory.tenant_id == tenant_id)

        if approver_id:
            query = query.filter(ApprovalHistory.approver_id == approver_id)

        total_approvals = query.count()
        pending = query.filter(ApprovalHistory.status == ApprovalStatus.PENDING).count()
        approved = query.filter(ApprovalHistory.status == ApprovalStatus.APPROVED).count()
        rejected = query.filter(ApprovalHistory.status == ApprovalStatus.REJECTED).count()
        changes_requested = query.filter(
            ApprovalHistory.status == ApprovalStatus.CHANGES_REQUESTED
        ).count()

        # Calculate average approval time
        approved_records = query.filter(
            and_(
                ApprovalHistory.status == ApprovalStatus.APPROVED,
                ApprovalHistory.approved_at.isnot(None)
            )
        ).all()

        avg_approval_time = None
        if approved_records:
            total_hours = sum([
                (record.approved_at - record.created_at).total_seconds() / 3600
                for record in approved_records
            ])
            avg_approval_time = total_hours / len(approved_records)

        return ApprovalStatistics(
            total_approvals=total_approvals,
            pending=pending,
            approved=approved,
            rejected=rejected,
            changes_requested=changes_requested,
            avg_approval_time_hours=avg_approval_time
        )


# Import for type checking
from app.modules.approvals.schemas import ApprovalStatusEnum
