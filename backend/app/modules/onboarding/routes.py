"""
Onboarding API Routes
Company onboarding workflow endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.onboarding.schemas import (
    OnboardingProgressResponse,
    CompanyProfileStepUpdate,
    FinanceConfigStepUpdate,
    IntegrationSelectionUpdate,
    SecuritySettingsUpdate,
    OnboardingStepResponse,
    OnboardingCompleteResponse
)
from app.modules.onboarding.service import OnboardingService
from app.modules.users.models import User
from app.core.response import success_response
from app.exceptions import TranslatrixException
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/{company_id}/progress", response_model=OnboardingProgressResponse)
async def get_onboarding_progress(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get onboarding progress for a company
    Returns completion status of all onboarding steps
    """
    try:
        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.get_onboarding_progress(company_id, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("get_onboarding_progress_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.put("/{company_id}/steps/company-profile", response_model=OnboardingStepResponse)
async def update_company_profile_step(
    company_id: str,
    profile_data: CompanyProfileStepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update company profile onboarding step
    Updates company profile and marks step as completed
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_company_profile_step(company_id, profile_data, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("update_company_profile_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.put("/{company_id}/steps/finance-config", response_model=OnboardingStepResponse)
async def update_finance_config_step(
    company_id: str,
    finance_data: FinanceConfigStepUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update finance configuration onboarding step
    Sets company financial settings and marks step as completed
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_finance_config_step(company_id, finance_data, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("update_finance_config_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.put("/{company_id}/steps/integration-selection", response_model=OnboardingStepResponse)
async def update_integration_selection_step(
    company_id: str,
    integration_data: IntegrationSelectionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update integration selection onboarding step
    Saves selected accounting software and storage sources
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_integration_selection_step(company_id, integration_data, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("update_integration_selection_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/{company_id}/steps/users-invited", response_model=OnboardingStepResponse)
async def mark_users_invited_step(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark users invited step as completed
    Called after inviting team members
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.mark_users_invited_step(company_id, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("mark_users_invited_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.put("/{company_id}/steps/security-settings", response_model=OnboardingStepResponse)
async def update_security_settings_step(
    company_id: str,
    security_data: SecuritySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update security settings onboarding step
    Configures company security preferences
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_security_settings_step(company_id, security_data, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("update_security_settings_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/{company_id}/complete", response_model=OnboardingCompleteResponse)
async def complete_onboarding(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete the onboarding process
    Verifies all steps are completed and finalizes onboarding
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.complete_onboarding(company_id, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("complete_onboarding_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/{company_id}/next-step", response_model=dict)
async def get_next_onboarding_step(
    company_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the next recommended onboarding step
    Helps guide users through the onboarding process
    """
    try:
        service = OnboardingService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        progress = service.get_onboarding_progress(company_id, tenant_id)

        # Determine next step
        next_step = None
        if not progress["company_profile_completed"]:
            next_step = {
                "step": "company_profile",
                "title": "Complete Company Profile",
                "description": "Add your company details and contact information"
            }
        elif not progress["finance_config_completed"]:
            next_step = {
                "step": "finance_config",
                "title": "Configure Financial Settings",
                "description": "Set your default currency, language, and fiscal year"
            }
        elif not progress["integration_selected"]:
            next_step = {
                "step": "integration_selected",
                "title": "Select Integrations",
                "description": "Choose your accounting software and storage sources"
            }
        elif not progress["users_invited"]:
            next_step = {
                "step": "users_invited",
                "title": "Invite Team Members",
                "description": "Add users to your company workspace"
            }
        elif not progress["security_settings_completed"]:
            next_step = {
                "step": "security_settings",
                "title": "Configure Security Settings",
                "description": "Set up security preferences for your account"
            }
        else:
            next_step = {
                "step": "complete",
                "title": "Complete Onboarding",
                "description": "Finalize your setup and start using TRANSLATRIX PRO"
            }

        return success_response(
            data={
                "next_step": next_step,
                "completion_percentage": progress["completion_percentage"]
            },
            message="Next onboarding step retrieved successfully"
        )
    except TranslatrixException as e:
        logger.error("get_next_step_failed", company_id=company_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
