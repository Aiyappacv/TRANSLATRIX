"""
Company Service
Business logic for company management
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import structlog

from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanyCreate, CompanyUpdate
from app.modules.onboarding.repository import OnboardingRepository
from app.core.tenant_context import get_current_tenant_id
from app.exceptions import (
    CompanyNotFoundError,
    DuplicateEntryError,
    ValidationError,
    AuthorizationError
)

logger = structlog.get_logger(__name__)


class CompanyService:
    """Service for company operations"""

    def __init__(self, db: Session):
        self.db = db
        self.company_repo = CompanyRepository(db)
        self.onboarding_repo = OnboardingRepository(db)

    def create_company(
        self,
        tenant_id: str,
        company_data: CompanyCreate
    ) -> Dict[str, Any]:
        """
        Create a new company for a tenant

        Args:
            tenant_id: Tenant UUID
            company_data: Company creation data

        Returns:
            Created company information

        Raises:
            DuplicateEntryError: If company email already exists
        """
        # Check if company email already exists
        existing_company = self.company_repo.get_by_email(company_data.email)
        if existing_company:
            logger.warning("duplicate_company_email", email=company_data.email)
            raise DuplicateEntryError(f"Company with email '{company_data.email}' already exists")

        # Create company
        company = self.company_repo.create(
            tenant_id=tenant_id,
            legal_name=company_data.legal_name,
            trading_name=company_data.trading_name,
            country=company_data.country,
            industry=company_data.industry,
            registration_number=company_data.registration_number,
            tax_number=company_data.tax_number,
            vat_number=company_data.vat_number,
            gst_number=company_data.gst_number,
            primary_contact=company_data.primary_contact,
            email=company_data.email,
            phone=company_data.phone,
            website=company_data.website,
            address_line1=company_data.address_line1,
            address_line2=company_data.address_line2,
            city=company_data.city,
            state=company_data.state,
            postal_code=company_data.postal_code,
            country_code=company_data.country_code,
            default_currency=company_data.default_currency,
            default_language=company_data.default_language,
            timezone=company_data.timezone,
            fiscal_year_start=company_data.fiscal_year_start
        )

        # Create onboarding record
        self.onboarding_repo.create(company_id=company.id)

        logger.info(
            "company_created",
            company_id=str(company.id),
            tenant_id=tenant_id,
            name=company.legal_name
        )

        return {
            "id": str(company.id),
            "tenant_id": str(company.tenant_id),
            "legal_name": company.legal_name,
            "email": company.email,
            "created_at": company.created_at.isoformat()
        }

    def get_company(self, company_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get company by ID

        Args:
            company_id: Company UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Company information

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If company doesn't belong to tenant
        """
        company = self.company_repo.get_by_id(company_id)
        if not company:
            logger.warning("company_not_found", company_id=company_id)
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_company_access",
                company_id=company_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this company")

        return {
            "id": str(company.id),
            "tenant_id": str(company.tenant_id),
            "legal_name": company.legal_name,
            "trading_name": company.trading_name,
            "country": company.country,
            "industry": company.industry,
            "registration_number": company.registration_number,
            "tax_number": company.tax_number,
            "vat_number": company.vat_number,
            "gst_number": company.gst_number,
            "primary_contact": company.primary_contact,
            "email": company.email,
            "phone": company.phone,
            "website": company.website,
            "address_line1": company.address_line1,
            "address_line2": company.address_line2,
            "city": company.city,
            "state": company.state,
            "postal_code": company.postal_code,
            "country_code": company.country_code,
            "default_currency": company.default_currency,
            "default_language": company.default_language,
            "timezone": company.timezone,
            "fiscal_year_start": company.fiscal_year_start,
            "created_at": company.created_at.isoformat(),
            "updated_at": company.updated_at.isoformat()
        }

    def get_companies_by_tenant(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all companies for a tenant

        Args:
            tenant_id: Tenant UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Paginated list of companies
        """
        companies = self.company_repo.get_by_tenant_id(tenant_id)
        total = len(companies)

        # Manual pagination
        paginated_companies = companies[skip:skip + limit]

        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1

        return {
            "items": [
                {
                    "id": str(c.id),
                    "tenant_id": str(c.tenant_id),
                    "legal_name": c.legal_name,
                    "trading_name": c.trading_name,
                    "country": c.country,
                    "email": c.email,
                    "created_at": c.created_at.isoformat()
                }
                for c in paginated_companies
            ],
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages
        }

    def update_company(
        self,
        company_id: str,
        company_data: CompanyUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update company information

        Args:
            company_id: Company UUID
            company_data: Company update data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Updated company information

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If company doesn't belong to tenant
        """
        company = self.company_repo.get_by_id(company_id)
        if not company:
            logger.warning("company_not_found", company_id=company_id)
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_company_access",
                company_id=company_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this company")

        # Update company with only provided fields
        update_data = company_data.model_dump(exclude_unset=True)
        company = self.company_repo.update(company_id, **update_data)

        logger.info("company_updated", company_id=company_id)

        return {
            "id": str(company.id),
            "tenant_id": str(company.tenant_id),
            "legal_name": company.legal_name,
            "email": company.email,
            "updated_at": company.updated_at.isoformat()
        }

    def delete_company(self, company_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Delete a company (soft delete recommended in production)

        Args:
            company_id: Company UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Deletion confirmation

        Raises:
            CompanyNotFoundError: If company not found
            AuthorizationError: If company doesn't belong to tenant
        """
        company = self.company_repo.get_by_id(company_id)
        if not company:
            logger.warning("company_not_found", company_id=company_id)
            raise CompanyNotFoundError("Company not found")

        # Tenant isolation check
        if tenant_id and str(company.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_company_access",
                company_id=company_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this company")

        # In production, implement soft delete instead
        # For now, we'll just log the intent
        logger.warning(
            "company_deletion_requested",
            company_id=company_id,
            note="Soft delete should be implemented in production"
        )

        return {
            "message": "Company deletion requested",
            "company_id": company_id,
            "note": "Soft delete would be implemented in production"
        }
