"""
Onboarding Repository
Database operations for company onboarding
"""
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.modules.onboarding.models import CompanyOnboarding


class OnboardingRepository:
    """Repository for onboarding database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, company_id: str | UUID) -> CompanyOnboarding:
        """Create onboarding record for company"""
        if isinstance(company_id, str):
            company_id = UUID(company_id)

        onboarding = CompanyOnboarding(company_id=company_id)
        self.db.add(onboarding)
        self.db.commit()
        self.db.refresh(onboarding)
        return onboarding

    def get_by_company_id(self, company_id: str | UUID) -> Optional[CompanyOnboarding]:
        """Get onboarding by company ID"""
        if isinstance(company_id, str):
            company_id = UUID(company_id)
        return self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.company_id == company_id
        ).first()

    def mark_company_profile_completed(self, onboarding_id: str | UUID) -> CompanyOnboarding:
        """Mark company profile step as completed"""
        if isinstance(onboarding_id, str):
            onboarding_id = UUID(onboarding_id)

        onboarding = self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.id == onboarding_id
        ).first()
        if onboarding:
            onboarding.company_profile_completed = True
            onboarding.company_profile_completed_at = datetime.utcnow()
            self._check_completion(onboarding)
            self.db.commit()
            self.db.refresh(onboarding)
        return onboarding

    def mark_finance_config_completed(self, onboarding_id: str | UUID) -> CompanyOnboarding:
        """Mark finance config step as completed"""
        if isinstance(onboarding_id, str):
            onboarding_id = UUID(onboarding_id)

        onboarding = self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.id == onboarding_id
        ).first()
        if onboarding:
            onboarding.finance_config_completed = True
            onboarding.finance_config_completed_at = datetime.utcnow()
            self._check_completion(onboarding)
            self.db.commit()
            self.db.refresh(onboarding)
        return onboarding

    def mark_users_invited(self, onboarding_id: str | UUID) -> CompanyOnboarding:
        """Mark users invited step as completed"""
        if isinstance(onboarding_id, str):
            onboarding_id = UUID(onboarding_id)

        onboarding = self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.id == onboarding_id
        ).first()
        if onboarding:
            onboarding.users_invited = True
            onboarding.users_invited_at = datetime.utcnow()
            self._check_completion(onboarding)
            self.db.commit()
            self.db.refresh(onboarding)
        return onboarding

    def mark_integration_selected(
        self,
        onboarding_id: str | UUID,
        accounting_software: str,
        storage_sources: list
    ) -> CompanyOnboarding:
        """Mark integration selection step as completed"""
        if isinstance(onboarding_id, str):
            onboarding_id = UUID(onboarding_id)

        onboarding = self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.id == onboarding_id
        ).first()
        if onboarding:
            onboarding.integration_selected = True
            onboarding.integration_selected_at = datetime.utcnow()
            onboarding.selected_accounting_software = accounting_software
            onboarding.selected_storage_sources = storage_sources
            self._check_completion(onboarding)
            self.db.commit()
            self.db.refresh(onboarding)
        return onboarding

    def mark_security_settings_completed(self, onboarding_id: str | UUID) -> CompanyOnboarding:
        """Mark security settings step as completed"""
        if isinstance(onboarding_id, str):
            onboarding_id = UUID(onboarding_id)

        onboarding = self.db.query(CompanyOnboarding).filter(
            CompanyOnboarding.id == onboarding_id
        ).first()
        if onboarding:
            onboarding.security_settings_completed = True
            onboarding.security_settings_completed_at = datetime.utcnow()
            self._check_completion(onboarding)
            self.db.commit()
            self.db.refresh(onboarding)
        return onboarding

    def _check_completion(self, onboarding: CompanyOnboarding) -> None:
        """Check if all steps are completed"""
        all_completed = all([
            onboarding.company_profile_completed,
            onboarding.finance_config_completed,
            onboarding.users_invited,
            onboarding.integration_selected,
            onboarding.security_settings_completed
        ])

        if all_completed and not onboarding.onboarding_completed:
            onboarding.onboarding_completed = True
            onboarding.onboarding_completed_at = datetime.utcnow()
