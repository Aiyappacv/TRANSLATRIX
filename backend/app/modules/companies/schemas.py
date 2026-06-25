"""
Company Schemas
Pydantic models for company requests and responses
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    """Base company schema"""
    legal_name: str = Field(..., min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    country: str = Field(..., min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_number: Optional[str] = Field(None, max_length=100)
    vat_number: Optional[str] = Field(None, max_length=100)
    gst_number: Optional[str] = Field(None, max_length=100)


class CompanyContactInfo(BaseModel):
    """Company contact information schema"""
    primary_contact: Optional[str] = Field(None, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)


class CompanyAddress(BaseModel):
    """Company address schema"""
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, max_length=10)


class CompanyFinancialSettings(BaseModel):
    """Company financial settings schema"""
    default_currency: str = Field(default="USD", max_length=10)
    default_language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    fiscal_year_start: Optional[str] = Field(None, max_length=5)


class CompanyCreate(CompanyBase, CompanyContactInfo, CompanyAddress, CompanyFinancialSettings):
    """Company creation schema - combined all fields"""
    pass


class CompanyUpdate(BaseModel):
    """Company update schema - all fields optional"""
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_number: Optional[str] = Field(None, max_length=100)
    vat_number: Optional[str] = Field(None, max_length=100)
    gst_number: Optional[str] = Field(None, max_length=100)

    primary_contact: Optional[str] = Field(None, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)

    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=20)
    country_code: Optional[str] = Field(None, max_length=10)

    default_currency: Optional[str] = Field(None, max_length=10)
    default_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    fiscal_year_start: Optional[str] = Field(None, max_length=5)


class CompanyResponse(CompanyBase, CompanyContactInfo, CompanyAddress, CompanyFinancialSettings):
    """Company response schema"""
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    """Company list response with pagination"""
    items: list[CompanyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class CompanyProfileUpdate(BaseModel):
    """Company profile update for onboarding"""
    legal_name: Optional[str] = Field(None, min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_number: Optional[str] = Field(None, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    website: Optional[str] = Field(None, max_length=255)


class CompanyFinanceConfigUpdate(BaseModel):
    """Company finance configuration update for onboarding"""
    default_currency: Optional[str] = Field(None, max_length=10)
    default_language: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    fiscal_year_start: Optional[str] = Field(None, max_length=5)
