"""
Company Repository
Database operations for companies
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from uuid import UUID

from app.modules.companies.models import Company


class CompanyRepository:
    """Repository for company database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, tenant_id: str | UUID, **kwargs) -> Company:
        """Create a new company"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)

        company = Company(tenant_id=tenant_id, **kwargs)
        self.db.add(company)
        self.db.commit()
        self.db.refresh(company)
        return company

    def get_by_id(self, company_id: str | UUID) -> Optional[Company]:
        """Get company by ID"""
        if isinstance(company_id, str):
            company_id = UUID(company_id)
        return self.db.query(Company).filter(Company.id == company_id).first()

    def get_by_tenant_id(self, tenant_id: str | UUID) -> List[Company]:
        """Get all companies for a tenant"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        return self.db.query(Company).filter(Company.tenant_id == tenant_id).all()

    def get_by_email(self, email: str) -> Optional[Company]:
        """Get company by email"""
        return self.db.query(Company).filter(Company.email == email).first()

    def update(self, company_id: str | UUID, **kwargs) -> Optional[Company]:
        """Update company"""
        company = self.get_by_id(company_id)
        if company:
            for key, value in kwargs.items():
                if hasattr(company, key):
                    setattr(company, key, value)
            self.db.commit()
            self.db.refresh(company)
        return company

    def count_by_tenant(self, tenant_id: str | UUID) -> int:
        """Count companies for a tenant"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        return self.db.query(Company).filter(Company.tenant_id == tenant_id).count()
