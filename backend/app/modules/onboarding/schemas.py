"""
Onboarding Schemas
Pydantic models for company onboarding requests and responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class OnboardingStepStatus(BaseModel):
    """Individual onboarding step status"""
    completed: bool
    completed_at: Optional[datetime] = None


class OnboardingProgressResponse(BaseModel):
    """Onboarding progress response"""
    id: str
    company_id: str

    # Step statuses
    company_profile_completed: bool
    finance_config_completed: bool
    users_invited: bool
    integration_selected: bool
    security_settings_completed: bool
    onboarding_completed: bool

    # Completion timestamps
    company_profile_completed_at: Optional[datetime]
    finance_config_completed_at: Optional[datetime]
    users_invited_at: Optional[datetime]
    integration_selected_at: Optional[datetime]
    security_settings_completed_at: Optional[datetime]
    onboarding_completed_at: Optional[datetime]

    # Integration selections
    selected_accounting_software: Optional[str]
    selected_storage_sources: Optional[List[str]]

    # Calculated
    completion_percentage: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyProfileStepUpdate(BaseModel):
    """Company profile onboarding step update"""
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_number: Optional[str] = Field(None, max_length=100)


class FinanceConfigStepUpdate(BaseModel):
    """Finance configuration onboarding step update"""
    default_currency: str = Field(..., max_length=10)
    default_language: str = Field(..., max_length=10)
    timezone: str = Field(..., max_length=50)
    fiscal_year_start: Optional[str] = Field(None, max_length=5)


class IntegrationSelectionUpdate(BaseModel):
    """Integration selection onboarding step update"""
    accounting_software: str = Field(
        ...,
        description="Selected accounting software (sap, quickbooks, xero, zoho, sage, netsuite)"
    )
    storage_sources: List[str] = Field(
        default_factory=list,
        description="Selected storage sources (google_drive, dropbox, onedrive, sharepoint, box)"
    )


class SecuritySettingsUpdate(BaseModel):
    """Security settings onboarding step update"""
    require_2fa: bool = False
    password_expiry_days: Optional[int] = Field(None, ge=0, le=365)
    session_timeout_minutes: Optional[int] = Field(None, ge=5, le=1440)
    ip_whitelist: Optional[List[str]] = None


class OnboardingStepResponse(BaseModel):
    """Generic onboarding step completion response"""
    step_name: str
    completed: bool
    message: str
    completion_percentage: int


class OnboardingCompleteResponse(BaseModel):
    """Onboarding completion response"""
    onboarding_completed: bool
    completion_percentage: int
    message: str
    next_steps: List[str]
