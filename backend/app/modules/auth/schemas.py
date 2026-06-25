"""
Auth Schemas
Pydantic models for authentication requests and responses
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class CompanyRegistrationRequest(BaseModel):
    """Company registration request"""
    # Company details
    legal_name: str = Field(..., min_length=2, max_length=255)
    trading_name: Optional[str] = Field(None, max_length=255)
    country: str = Field(..., min_length=2, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    registration_number: Optional[str] = Field(None, max_length=100)
    tax_number: Optional[str] = Field(None, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)

    # Financial settings
    default_currency: str = Field(default="USD", max_length=10)
    default_language: str = Field(default="en", max_length=10)
    timezone: str = Field(default="UTC", max_length=50)

    # Admin user
    admin_first_name: str = Field(..., min_length=1, max_length=100)
    admin_last_name: str = Field(..., min_length=1, max_length=100)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=100)


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Token response after successful login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: str
    is_active: bool
    is_super_admin: bool
    tenant_id: Optional[str]
    company_id: Optional[str]
    role_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordChangeRequest(BaseModel):
    """Password change request"""
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    """Password reset request"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8)
