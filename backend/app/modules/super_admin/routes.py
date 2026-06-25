"""
Super Admin Routes
Platform administration endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from uuid import UUID
import structlog

from app.database import get_db
from app.dependencies import get_current_super_admin
from app.modules.users.models import User
from app.modules.super_admin.service import SuperAdminService
from app.modules.super_admin.schemas import (
    DashboardResponse,
    CompanyListResponse,
    CompanyDetail,
    CompanySuspendRequest,
    CompanyReactivateRequest,
    SystemHealthResponse,
    JobQueueResponse,
    IntegrationsResponse,
    AuditLogListResponse,
)
from app.core.response import success_response, error_response

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/dashboard", response_model=DashboardResponse)
async def get_platform_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get platform-wide dashboard statistics
    Super admin only
    """
    logger.info("get_platform_dashboard", user_id=str(current_user.id))

    service = SuperAdminService(db)
    dashboard = service.get_platform_dashboard()

    return dashboard


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    page: int = 1,
    page_size: int = 50,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    List all companies with filtering and pagination
    Super admin only
    """
    logger.info(
        "list_companies",
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
        status=status,
    )

    service = SuperAdminService(db)
    companies, total = service.list_companies(
        page=page, page_size=page_size, status=status, search=search
    )

    return CompanyListResponse(
        companies=companies,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/companies/{company_id}", response_model=CompanyDetail)
async def get_company_detail(
    company_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get detailed company information
    Super admin only
    """
    logger.info("get_company_detail", user_id=str(current_user.id), company_id=str(company_id))

    service = SuperAdminService(db)
    company = service.get_company_detail(company_id)

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return company


@router.post("/companies/{company_id}/suspend")
async def suspend_company(
    company_id: UUID,
    request_data: CompanySuspendRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Suspend a company's access to the platform
    Super admin only
    """
    logger.info(
        "suspend_company",
        user_id=str(current_user.id),
        company_id=str(company_id),
        reason=request_data.reason,
    )

    # Get IP address
    ip_address = request.client.host if request.client else None

    service = SuperAdminService(db)
    success = service.suspend_company(
        company_id=company_id,
        admin_user_id=current_user.id,
        reason=request_data.reason,
        ip_address=ip_address,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return success_response(
        data={"company_id": str(company_id), "status": "suspended"},
        message="Company suspended successfully",
    )


@router.post("/companies/{company_id}/reactivate")
async def reactivate_company(
    company_id: UUID,
    request_data: CompanyReactivateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Reactivate a suspended company
    Super admin only
    """
    logger.info(
        "reactivate_company",
        user_id=str(current_user.id),
        company_id=str(company_id),
    )

    # Get IP address
    ip_address = request.client.host if request.client else None

    service = SuperAdminService(db)
    success = service.reactivate_company(
        company_id=company_id,
        admin_user_id=current_user.id,
        notes=request_data.notes,
        ip_address=ip_address,
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )

    return success_response(
        data={"company_id": str(company_id), "status": "active"},
        message="Company reactivated successfully",
    )


@router.get("/system-health", response_model=SystemHealthResponse)
async def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get health status of all system components
    Super admin only
    """
    logger.info("get_system_health", user_id=str(current_user.id))

    service = SuperAdminService(db)
    health = service.get_system_health()

    return health


@router.get("/job-queues", response_model=JobQueueResponse)
async def get_job_queues(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get metrics for all job queues
    Super admin only
    """
    logger.info("get_job_queues", user_id=str(current_user.id))

    service = SuperAdminService(db)
    queues = service.get_job_queue_metrics()

    return queues


@router.get("/integrations", response_model=IntegrationsResponse)
async def get_integrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get status of all external integrations
    Super admin only
    """
    logger.info("get_integrations", user_id=str(current_user.id))

    service = SuperAdminService(db)
    integrations = service.get_integrations()

    return integrations


@router.get("/audit-logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = 1,
    page_size: int = 50,
    action: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    """
    Get platform audit logs
    Super admin only
    """
    logger.info(
        "get_audit_logs",
        user_id=str(current_user.id),
        page=page,
        page_size=page_size,
    )

    service = SuperAdminService(db)
    logs, total = service.get_audit_logs(page=page, page_size=page_size, action=action)

    return AuditLogListResponse(
        logs=logs,
        total=total,
        page=page,
        page_size=page_size,
    )
