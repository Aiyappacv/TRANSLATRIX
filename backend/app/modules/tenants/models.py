"""
Tenant Model
Multi-tenant isolation and platform management
"""
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database import Base


class TenantStatus(enum.Enum):
    """Tenant status enumeration"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"
    TRIAL = "trial"


class Tenant(Base):
    """
    Tenant model for multi-tenancy
    Each company belongs to a tenant
    """
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    status = Column(
        SQLEnum(TenantStatus),
        nullable=False,
        default=TenantStatus.ACTIVE,
        index=True
    )
    plan = Column(String(50), nullable=True)  # starter, professional, enterprise
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    companies = relationship("Company", back_populates="tenant", cascade="all, delete-orphan")
    users = relationship("User", back_populates="tenant")

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name}, status={self.status})>"

    def is_active(self) -> bool:
        """Check if tenant is active"""
        return self.status == TenantStatus.ACTIVE
