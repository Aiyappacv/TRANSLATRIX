"""
Company Onboarding Model
Track company onboarding progress
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from app.database import Base


class CompanyOnboarding(Base):
    """
    Company onboarding workflow tracking
    Tracks completion of onboarding steps
    """
    __tablename__ = "company_onboarding"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    # Onboarding Steps
    company_profile_completed = Column(Boolean, nullable=False, default=False)
    finance_config_completed = Column(Boolean, nullable=False, default=False)
    users_invited = Column(Boolean, nullable=False, default=False)
    integration_selected = Column(Boolean, nullable=False, default=False)
    security_settings_completed = Column(Boolean, nullable=False, default=False)
    onboarding_completed = Column(Boolean, nullable=False, default=False)

    # Selected Integrations
    selected_accounting_software = Column(String(50), nullable=True)  # sap, quickbooks, xero, etc.
    selected_storage_sources = Column(JSON, nullable=True)  # List of storage sources

    # Completion Timestamps
    company_profile_completed_at = Column(DateTime, nullable=True)
    finance_config_completed_at = Column(DateTime, nullable=True)
    users_invited_at = Column(DateTime, nullable=True)
    integration_selected_at = Column(DateTime, nullable=True)
    security_settings_completed_at = Column(DateTime, nullable=True)
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    company = relationship("Company", back_populates="onboarding")

    def get_completion_percentage(self) -> int:
        """Calculate onboarding completion percentage"""
        steps = [
            self.company_profile_completed,
            self.finance_config_completed,
            self.users_invited,
            self.integration_selected,
            self.security_settings_completed,
        ]
        completed = sum(1 for step in steps if step)
        return int((completed / len(steps)) * 100)

    def __repr__(self) -> str:
        return f"<CompanyOnboarding(company_id={self.company_id}, completed={self.onboarding_completed})>"
