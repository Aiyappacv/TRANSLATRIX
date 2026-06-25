"""
Tenant Repository
Database operations for tenants
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from app.modules.tenants.models import Tenant, TenantStatus


class TenantRepository:
    """Repository for tenant database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, plan: Optional[str] = None) -> Tenant:
        """Create a new tenant"""
        tenant = Tenant(
            name=name,
            plan=plan,
            status=TenantStatus.ACTIVE
        )
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_by_id(self, tenant_id: str | UUID) -> Optional[Tenant]:
        """Get tenant by ID"""
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        return self.db.query(Tenant).filter(Tenant.id == tenant_id).first()

    def get_by_name(self, name: str) -> Optional[Tenant]:
        """Get tenant by name"""
        return self.db.query(Tenant).filter(Tenant.name == name).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """Get all tenants with pagination"""
        return self.db.query(Tenant).offset(skip).limit(limit).all()

    def update_status(self, tenant_id: str | UUID, status: TenantStatus) -> Optional[Tenant]:
        """Update tenant status"""
        tenant = self.get_by_id(tenant_id)
        if tenant:
            tenant.status = status
            self.db.commit()
            self.db.refresh(tenant)
        return tenant

    def count(self) -> int:
        """Count total tenants"""
        return self.db.query(Tenant).count()

    def get_active_tenants(self) -> List[Tenant]:
        """Get all active tenants"""
        return self.db.query(Tenant).filter(Tenant.status == TenantStatus.ACTIVE).all()
