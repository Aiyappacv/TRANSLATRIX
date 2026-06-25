"""
Analytics Routes
API endpoints for analytics and reporting
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.modules.analytics.service import AnalyticsService
from app.modules.analytics.schemas import (
    DashboardStatistics,
    ProcessingMetricsResponse,
    UserActivityResponse
)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStatistics)
def get_dashboard_statistics(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get dashboard statistics"""
    stats = AnalyticsService.get_dashboard_statistics(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        start_date=start_date,
        end_date=end_date
    )
    return DashboardStatistics(**stats)


@router.get("/processing-metrics", response_model=ProcessingMetricsResponse)
def get_processing_metrics(
    period_type: str = Query("daily", regex="^(hourly|daily|weekly|monthly)$"),
    limit: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get processing metrics over time"""
    metrics = AnalyticsService.get_processing_metrics(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        period_type=period_type,
        limit=limit
    )
    return ProcessingMetricsResponse(**metrics)


@router.get("/user-activity", response_model=UserActivityResponse)
def get_user_activity(
    user_id: Optional[UUID] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Get user activity statistics"""
    activity = AnalyticsService.get_user_activity(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        user_id=user_id,
        start_date=start_date,
        end_date=end_date
    )
    return UserActivityResponse(**activity)
