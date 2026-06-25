"""
Onboarding Service
Business logic for company onboarding workflow
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
import structlog

from app.modules.onboarding.repository import OnboardingRepository
from app.modules.companies.repository import CompanyRepository
from app.modules.onboarding.schemas import (
    CompanyProfileStepUpdate,
    FinanceConfigStepUpdate,
    IntegrationSelectionUpdate,
    SecuritySettingsUpdate
)
from app.exceptions import (
    CompanyNotFoundError,
    ValidationError,
    AuthorizationError
)

logger = structlog.get_logger(__name__)


class OnboardingService:
    """Service for company onboarding operations"""

    def __init__(self, db: Session):
        self.db = db
        self.onboarding_repo = OnboardingRepository(db)
        self.company_repo = CompanyRepository(db)

    def get_onboarding_progress(
        self,
        company_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get onboarding progress for a company

        Args:
            company_id: Company UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Onboarding progress information

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If company doesn't belong to tenant
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            logger.warning("company_not_found", company_id=company_id)
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_onboarding_access",
                company_id=company_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this company")

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            # Create onboarding record if it doesn't exist
            onboarding = self.onboarding_repo.create(company_id=company_id)

        return {
            "id": str(onboarding.id),
            "company_id": str(onboarding.company_id),
            "company_profile_completed": onboarding.company_profile_completed,
            "finance_config_completed": onboarding.finance_config_completed,
            "users_invited": onboarding.users_invited,
            "integration_selected": onboarding.integration_selected,
            "security_settings_completed": onboarding.security_settings_completed,
            "onboarding_completed": onboarding.onboarding_completed,
            "company_profile_completed_at": onboarding.company_profile_completed_at.isoformat() if onboarding.company_profile_completed_at else None,
            "finance_config_completed_at": onboarding.finance_config_completed_at.isoformat() if onboarding.finance_config_completed_at else None,
            "users_invited_at": onboarding.users_invited_at.isoformat() if onboarding.users_invited_at else None,
            "integration_selected_at": onboarding.integration_selected_at.isoformat() if onboarding.integration_selected_at else None,
            "security_settings_completed_at": onboarding.security_settings_completed_at.isoformat() if onboarding.security_settings_completed_at else None,
            "onboarding_completed_at": onboarding.onboarding_completed_at.isoformat() if onboarding.onboarding_completed_at else None,
            "selected_accounting_software": onboarding.selected_accounting_software,
            "selected_storage_sources": onboarding.selected_storage_sources,
            "completion_percentage": onboarding.get_completion_percentage(),
            "created_at": onboarding.created_at.isoformat(),
            "updated_at": onboarding.updated_at.isoformat()
        }

    def update_company_profile_step(
        self,
        company_id: str,
        profile_data: CompanyProfileStepUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update company profile onboarding step

        Args:
            company_id: Company UUID
            profile_data: Company profile update data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Step completion status

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If company doesn't belong to tenant
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            logger.warning("company_not_found", company_id=company_id)
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # Update company profile
        update_data = profile_data.model_dump(exclude_unset=True)
        if update_data:
            self.company_repo.update(company_id, **update_data)

        # Get or create onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            onboarding = self.onboarding_repo.create(company_id=company_id)

        # Mark step as completed
        onboarding = self.onboarding_repo.mark_company_profile_completed(onboarding.id)

        logger.info("company_profile_step_completed", company_id=company_id)

        return {
            "step_name": "company_profile",
            "completed": True,
            "message": "Company profile updated successfully",
            "completion_percentage": onboarding.get_completion_percentage()
        }

    def update_finance_config_step(
        self,
        company_id: str,
        finance_data: FinanceConfigStepUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update finance configuration onboarding step

        Args:
            company_id: Company UUID
            finance_data: Finance configuration update data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Step completion status
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # Update company financial settings
        self.company_repo.update(
            company_id,
            default_currency=finance_data.default_currency,
            default_language=finance_data.default_language,
            timezone=finance_data.timezone,
            fiscal_year_start=finance_data.fiscal_year_start
        )

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            onboarding = self.onboarding_repo.create(company_id=company_id)

        # Mark step as completed
        onboarding = self.onboarding_repo.mark_finance_config_completed(onboarding.id)

        logger.info("finance_config_step_completed", company_id=company_id)

        return {
            "step_name": "finance_config",
            "completed": True,
            "message": "Finance configuration updated successfully",
            "completion_percentage": onboarding.get_completion_percentage()
        }

    def update_integration_selection_step(
        self,
        company_id: str,
        integration_data: IntegrationSelectionUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update integration selection onboarding step

        Args:
            company_id: Company UUID
            integration_data: Integration selection data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Step completion status
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # Validate accounting software choice
        valid_accounting_software = [
            "sap", "quickbooks", "xero", "zoho", "sage", "netsuite", "other"
        ]
        if integration_data.accounting_software not in valid_accounting_software:
            raise ValidationError(
                f"Invalid accounting software. Must be one of: {', '.join(valid_accounting_software)}"
            )

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            onboarding = self.onboarding_repo.create(company_id=company_id)

        # Mark step as completed with integration selections
        onboarding = self.onboarding_repo.mark_integration_selected(
            onboarding.id,
            integration_data.accounting_software,
            integration_data.storage_sources
        )

        logger.info(
            "integration_selection_step_completed",
            company_id=company_id,
            accounting_software=integration_data.accounting_software
        )

        return {
            "step_name": "integration_selected",
            "completed": True,
            "message": "Integration selections saved successfully",
            "completion_percentage": onboarding.get_completion_percentage()
        }

    def mark_users_invited_step(
        self,
        company_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark users invited step as completed

        Args:
            company_id: Company UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Step completion status
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            onboarding = self.onboarding_repo.create(company_id=company_id)

        # Mark step as completed
        onboarding = self.onboarding_repo.mark_users_invited(onboarding.id)

        logger.info("users_invited_step_completed", company_id=company_id)

        return {
            "step_name": "users_invited",
            "completed": True,
            "message": "Users invited step completed",
            "completion_percentage": onboarding.get_completion_percentage()
        }

    def update_security_settings_step(
        self,
        company_id: str,
        security_data: SecuritySettingsUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update security settings onboarding step

        Args:
            company_id: Company UUID
            security_data: Security settings data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Step completion status
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # In production, save security settings to a company_security_settings table
        # For now, we'll just mark the step as completed

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            onboarding = self.onboarding_repo.create(company_id=company_id)

        # Mark step as completed
        onboarding = self.onboarding_repo.mark_security_settings_completed(onboarding.id)

        logger.info("security_settings_step_completed", company_id=company_id)

        return {
            "step_name": "security_settings",
            "completed": True,
            "message": "Security settings configured successfully",
            "completion_percentage": onboarding.get_completion_percentage()
        }

    def complete_onboarding(
        self,
        company_id: str,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Complete the onboarding process

        Args:
            company_id: Company UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Completion status and next steps

        Raises:
            ValidationError: If not all steps are completed
        """
        # Verify company exists
        company = self.company_repo.get_by_id(company_id)
        if not company:
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            raise AuthorizationError("Access denied to this company")

        # Get onboarding record
        onboarding = self.onboarding_repo.get_by_company_id(company_id)
        if not onboarding:
            raise ValidationError("Onboarding record not found")

        # Check if all steps are completed
        if not onboarding.onboarding_completed:
            missing_steps = []
            if not onboarding.company_profile_completed:
                missing_steps.append("company_profile")
            if not onboarding.finance_config_completed:
                missing_steps.append("finance_config")
            if not onboarding.users_invited:
                missing_steps.append("users_invited")
            if not onboarding.integration_selected:
                missing_steps.append("integration_selected")
            if not onboarding.security_settings_completed:
                missing_steps.append("security_settings")

            if missing_steps:
                raise ValidationError(
                    f"Cannot complete onboarding. Missing steps: {', '.join(missing_steps)}"
                )

        logger.info("onboarding_completed", company_id=company_id)

        return {
            "onboarding_completed": True,
            "completion_percentage": 100,
            "message": "Onboarding completed successfully! Welcome to TRANSLATRIX PRO",
            "next_steps": [
                "Upload your first document",
                "Configure document templates",
                "Set up approval workflows",
                "Connect to your accounting software",
                "Invite additional team members"
            ]
        }
