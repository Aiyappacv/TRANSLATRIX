"""
Company Model
Company profile and configuration
"""
from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class Company(Base):
    """
    Company model
    Stores company profile and financial configuration
    """
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)

    # Company Profile
    legal_name = Column(String(255), nullable=False)
    trading_name = Column(String(255), nullable=True)
    country = Column(String(100), nullable=False)
    industry = Column(String(100), nullable=True)
    registration_number = Column(String(100), nullable=True)
    tax_number = Column(String(100), nullable=True)  # VAT/GST/Tax ID
    vat_number = Column(String(100), nullable=True)
    gst_number = Column(String(100), nullable=True)

    # Contact Information
    primary_contact = Column(String(255), nullable=True)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    website = Column(String(255), nullable=True)

    # Address
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country_code = Column(String(10), nullable=True)

    # Financial Settings
    default_currency = Column(String(10), nullable=False, default="USD")
    default_language = Column(String(10), nullable=False, default="en")
    timezone = Column(String(50), nullable=False, default="UTC")
    fiscal_year_start = Column(String(5), nullable=True)  # e.g., "01-01"

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="companies")
    users = relationship("User", back_populates="company")
    onboarding = relationship("CompanyOnboarding", back_populates="company", uselist=False)

    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name={self.legal_name})>"
