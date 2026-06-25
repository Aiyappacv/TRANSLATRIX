"""
Analytics Service
Business logic for analytics and reporting
"""
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
import structlog

from app.modules.analytics.models import ProcessingMetrics
from app.modules.files.models import IngestedFile
from app.modules.entries.models import FinancialEntry
from app.modules.review.models import ReviewTask, ReviewStatus
from app.modules.sap.models import SAPPostingResult, SAPStatus

logger = structlog.get_logger(__name__)


class AnalyticsService:
    """Service for analytics and metrics"""

    @staticmethod
    def get_dashboard_statistics(
        db: Session,
        tenant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get dashboard statistics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        # Files statistics
        files_query = db.query(File).filter(
            and_(
                File.tenant_id == tenant_id,
                File.created_at >= start_date,
                File.created_at <= end_date
            )
        )

        total_files = files_query.count()
        processed_files = files_query.filter(File.processing_status == "completed").count()

        # Entries statistics
        entries_query = db.query(FinancialEntry).filter(
            and_(
                FinancialEntry.tenant_id == tenant_id,
                FinancialEntry.created_at >= start_date,
                FinancialEntry.created_at <= end_date
            )
        )

        total_entries = entries_query.count()

        # Review statistics
        review_query = db.query(ReviewTask).filter(
            and_(
                ReviewTask.tenant_id == tenant_id,
                ReviewTask.created_at >= start_date,
                ReviewTask.created_at <= end_date
            )
        )

        pending_reviews = review_query.filter(ReviewTask.status == ReviewStatus.PENDING).count()
        completed_reviews = review_query.filter(ReviewTask.status == ReviewStatus.COMPLETED).count()

        # SAP posting statistics
        sap_query = db.query(SAPPostingResult).filter(
            and_(
                SAPPostingResult.tenant_id == tenant_id,
                SAPPostingResult.created_at >= start_date,
                SAPPostingResult.created_at <= end_date
            )
        )

        posted_to_sap = sap_query.filter(SAPPostingResult.status == SAPStatus.POSTED).count()
        failed_sap = sap_query.filter(SAPPostingResult.status == SAPStatus.FAILED).count()

        # Calculate success rates
        processing_success_rate = (processed_files / total_files * 100) if total_files > 0 else 0
        sap_success_rate = (posted_to_sap / (posted_to_sap + failed_sap) * 100) if (posted_to_sap + failed_sap) > 0 else 0

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "files": {
                "total": total_files,
                "processed": processed_files,
                "processing_rate": round(processing_success_rate, 2)
            },
            "entries": {
                "total": total_entries
            },
            "reviews": {
                "pending": pending_reviews,
                "completed": completed_reviews,
                "total": pending_reviews + completed_reviews
            },
            "sap_posting": {
                "posted": posted_to_sap,
                "failed": failed_sap,
                "success_rate": round(sap_success_rate, 2)
            }
        }

    @staticmethod
    def get_processing_metrics(
        db: Session,
        tenant_id: UUID,
        period_type: str = "daily",
        limit: int = 30
    ) -> Dict[str, Any]:
        """Get processing metrics over time"""
        metrics = db.query(ProcessingMetrics).filter(
            and_(
                ProcessingMetrics.tenant_id == tenant_id,
                ProcessingMetrics.period_type == period_type
            )
        ).order_by(ProcessingMetrics.period_start.desc()).limit(limit).all()

        return {
            "period_type": period_type,
            "metrics": [
                {
                    "period_start": m.period_start.isoformat(),
                    "period_end": m.period_end.isoformat(),
                    "files_uploaded": m.files_uploaded,
                    "files_processed": m.files_processed,
                    "entries_created": m.entries_created,
                    "entries_approved": m.entries_approved,
                    "entries_posted": m.entries_posted,
                    "avg_processing_time": m.avg_total_processing_time,
                    "avg_confidence_score": m.avg_confidence_score
                }
                for m in metrics
            ]
        }

    @staticmethod
    def get_user_activity(
        db: Session,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get user activity statistics"""
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()

        # Files uploaded by user
        files_query = db.query(File).filter(
            and_(
                File.tenant_id == tenant_id,
                File.created_at >= start_date,
                File.created_at <= end_date
            )
        )

        if user_id:
            files_query = files_query.filter(File.uploaded_by == user_id)

        files_count = files_query.count()

        # Reviews completed by user
        reviews_query = db.query(ReviewTask).filter(
            and_(
                ReviewTask.tenant_id == tenant_id,
                ReviewTask.status == ReviewStatus.COMPLETED,
                ReviewTask.completed_at >= start_date,
                ReviewTask.completed_at <= end_date
            )
        )

        if user_id:
            reviews_query = reviews_query.filter(ReviewTask.assigned_to == user_id)

        reviews_count = reviews_query.count()

        return {
            "user_id": str(user_id) if user_id else "all",
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "files_uploaded": files_count,
            "reviews_completed": reviews_count
        }
