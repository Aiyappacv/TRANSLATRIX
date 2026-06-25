"""
Company API Routes
Company management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_current_tenant
from app.modules.companies.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse
)
from app.modules.companies.service import CompanyService
from app.modules.users.models import User
from app.modules.tenants.models import Tenant
from app.core.response import success_response, error_response
from app.exceptions import TranslatrixException
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_company(
    company_data: CompanyCreate,
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    Create a new company
    Requires authentication and tenant context
    """
    try:
        service = CompanyService(db)
        result = service.create_company(str(tenant.id), company_data)
        return success_response(
            data=result,
            message="Company created successfully"
        )
    except TranslatrixException as e:
        logger.error("company_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get company by ID
    Returns company details with tenant isolation
    """
    try:
        service = CompanyService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.get_company(company_id, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("get_company_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.get("/", response_model=CompanyListResponse)
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db)
):
    """
    List all companies for current tenant
    Supports pagination
    """
    try:
        service = CompanyService(db)
        result = service.get_companies_by_tenant(str(tenant.id), skip, limit)
        return result
    except TranslatrixException as e:
        logger.error("list_companies_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.put("/{company_id}", response_model=dict)
async def update_company(
    company_id: str,
    company_data: CompanyUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update company information
    Only accessible by company admin or authorized users
    """
    try:
        service = CompanyService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_company(company_id, company_data, tenant_id)
        return success_response(
            data=result,
            message="Company updated successfully"
        )
    except TranslatrixException as e:
        logger.error("update_company_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.delete("/{company_id}", response_model=dict)
async def delete_company(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a company
    Only accessible by company admin or super admin
    Note: Should implement soft delete in production
    """
    try:
        service = CompanyService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.delete_company(company_id, tenant_id)
        return success_response(
            data=result,
            message="Company deletion initiated"
        )
    except TranslatrixException as e:
        logger.error("delete_company_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/{company_id}/summary", response_model=dict)
async def get_company_summary(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get company summary with stats
    Includes user count, document count, etc.
    """
    try:
        service = CompanyService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        company_info = service.get_company(company_id, tenant_id)

        # In production, add additional stats here
        summary = {
            **company_info,
            "stats": {
                "total_users": 0,  # Will be calculated from user service
                "total_documents": 0,  # Will be calculated from file service
                "active_workflows": 0,  # Will be calculated from workflow service
            }
        }

        return success_response(
            data=summary,
            message="Company summary retrieved successfully"
        )
    except TranslatrixException as e:
        logger.error("get_company_summary_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )
