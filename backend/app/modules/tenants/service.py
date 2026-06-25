"""
Tenant Service
Business logic for tenant management
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import structlog

from app.modules.tenants.repository import TenantRepository
from app.modules.tenants.models import TenantStatus
from app.modules.tenants.schemas import TenantCreate, TenantUpdate, TenantStatusUpdate
from app.exceptions import (
    TenantNotFoundError,
    DuplicateEntryError,
    ValidationError
)

logger = structlog.get_logger(__name__)


class TenantService:
    """Service for tenant operations"""

    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantRepository(db)

    def create_tenant(self, tenant_data: TenantCreate) -> Dict[str, Any]:
        """
        Create a new tenant

        Args:
            tenant_data: Tenant creation data

        Returns:
            Created tenant information

        Raises:
            DuplicateEntryError: If tenant name already exists
        """
        # Check if tenant name already exists
        existing_tenant = self.tenant_repo.get_by_name(tenant_data.name)
        if existing_tenant:
            logger.warning("duplicate_tenant_name", name=tenant_data.name)
            raise DuplicateEntryError(f"Tenant with name '{tenant_data.name}' already exists")

        # Create tenant
        tenant = self.tenant_repo.create(
            name=tenant_data.name,
            plan=tenant_data.plan or "starter"
        )

        logger.info("tenant_created", tenant_id=str(tenant.id), name=tenant.name)

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "status": tenant.status.value,
            "plan": tenant.plan,
            "created_at": tenant.created_at.isoformat()
        }

    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get tenant by ID

        Args:
            tenant_id: Tenant UUID

        Returns:
            Tenant information

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            logger.warning("tenant_not_found", tenant_id=tenant_id)
            raise TenantNotFoundError("Tenant not found")

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "status": tenant.status.value,
            "plan": tenant.plan,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat()
        }

    def get_all_tenants(self, skip: int = 0, limit: int = 100) -> Dict[str, Any]:
        """
        Get all tenants with pagination

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Paginated list of tenants
        """
        tenants = self.tenant_repo.get_all(skip=skip, limit=limit)
        total = self.tenant_repo.count()

        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1

        return {
            "items": [
                {
                    "id": str(t.id),
                    "name": t.name,
                    "status": t.status.value,
                    "plan": t.plan,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat()
                }
                for t in tenants
            ],
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages
        }

    def update_tenant_status(self, tenant_id: str, status_data: TenantStatusUpdate) -> Dict[str, Any]:
        """
        Update tenant status

        Args:
            tenant_id: Tenant UUID
            status_data: New status

        Returns:
            Updated tenant information

        Raises:
            TenantNotFoundError: If tenant not found
        """
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            logger.warning("tenant_not_found", tenant_id=tenant_id)
            raise TenantNotFoundError("Tenant not found")

        # Convert enum to TenantStatus
        status_map = {
            "active": TenantStatus.ACTIVE,
            "suspended": TenantStatus.SUSPENDED,
            "inactive": TenantStatus.INACTIVE,
            "trial": TenantStatus.TRIAL
        }
        new_status = status_map.get(status_data.status.value)

        tenant = self.tenant_repo.update_status(tenant_id, new_status)

        logger.info(
            "tenant_status_updated",
            tenant_id=tenant_id,
            old_status=tenant.status.value if tenant else None,
            new_status=new_status.value
        )

        return {
            "id": str(tenant.id),
            "name": tenant.name,
            "status": tenant.status.value,
            "plan": tenant.plan,
            "updated_at": tenant.updated_at.isoformat()
        }

    def get_active_tenants(self) -> List[Dict[str, Any]]:
        """
        Get all active tenants

        Returns:
            List of active tenants
        """
        tenants = self.tenant_repo.get_active_tenants()

        return [
            {
                "id": str(t.id),
                "name": t.name,
                "status": t.status.value,
                "plan": t.plan,
                "created_at": t.created_at.isoformat()
            }
            for t in tenants
        ]
