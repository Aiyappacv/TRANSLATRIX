"""
Auth Service
Business logic for authentication and registration
"""
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.modules.auth.schemas import CompanyRegistrationRequest, LoginRequest
from app.modules.tenants.repository import TenantRepository
from app.modules.companies.repository import CompanyRepository
from app.modules.users.repository import UserRepository, RoleRepository
from app.modules.onboarding.repository import OnboardingRepository
from app.core.security import hash_password, verify_password, validate_password_strength
from app.core.jwt import create_access_token, create_refresh_token, decode_token
from app.exceptions import (
    AuthenticationError,
    UserNotFoundError,
    DuplicateEntryError,
    ValidationError
)
from app.config import settings


class AuthService:
    """Service for authentication operations"""

    def __init__(self, db: Session):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.company_repo = CompanyRepository(db)
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)
        self.onboarding_repo = OnboardingRepository(db)

    def register_company(self, request: CompanyRegistrationRequest) -> Dict[str, Any]:
        """
        Register a new company
        Creates: Tenant -> Company -> Admin User -> Onboarding
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(request.admin_password)
        if not is_valid:
            raise ValidationError(error_msg)

        # Check if email already exists
        existing_user = self.user_repo.get_by_email(request.admin_email)
        if existing_user:
            raise DuplicateEntryError("Email already registered")

        existing_company = self.company_repo.get_by_email(request.email)
        if existing_company:
            raise DuplicateEntryError("Company email already registered")

        # Create tenant
        tenant = self.tenant_repo.create(
            name=request.legal_name,
            plan="starter"  # Default plan
        )

        # Create company
        company = self.company_repo.create(
            tenant_id=tenant.id,
            legal_name=request.legal_name,
            trading_name=request.trading_name,
            country=request.country,
            industry=request.industry,
            registration_number=request.registration_number,
            tax_number=request.tax_number,
            email=request.email,
            phone=request.phone,
            default_currency=request.default_currency,
            default_language=request.default_language,
            timezone=request.timezone
        )

        # Get company_admin role
        admin_role = self.role_repo.get_by_name("company_admin")
        if not admin_role:
            raise ValidationError("Admin role not found. Please run seed data.")

        # Create admin user
        hashed_password = hash_password(request.admin_password)
        admin_user = self.user_repo.create(
            email=request.admin_email,
            hashed_password=hashed_password,
            tenant_id=tenant.id,
            company_id=company.id,
            role_id=admin_role.id,
            first_name=request.admin_first_name,
            last_name=request.admin_last_name,
            is_active=True,
            is_email_verified=False
        )

        # Create onboarding record
        onboarding = self.onboarding_repo.create(company_id=company.id)

        # Mark company profile as completed
        self.onboarding_repo.mark_company_profile_completed(onboarding.id)

        return {
            "tenant_id": str(tenant.id),
            "company_id": str(company.id),
            "user_id": str(admin_user.id),
            "message": "Company registered successfully"
        }

    def login(self, request: LoginRequest) -> Dict[str, Any]:
        """Authenticate user and return tokens"""
        # Get user by email
        user = self.user_repo.get_by_email(request.email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        # Verify password
        if not verify_password(request.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationError("Account is inactive")

        # Update last login
        self.user_repo.update_last_login(user.id)

        # Create tokens
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "is_super_admin": user.is_super_admin
            }
        }

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """Generate new access token from refresh token"""
        payload = decode_token(refresh_token)
        if not payload:
            raise AuthenticationError("Invalid refresh token")

        # Verify it's a refresh token
        if payload.get("type") != "refresh":
            raise AuthenticationError("Invalid token type")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationError("Invalid token payload")

        # Verify user exists and is active
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Create new access token
        token_data = {"sub": str(user.id), "email": user.email}
        access_token = create_access_token(token_data)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

    def get_current_user_info(self, user_id: str) -> Dict[str, Any]:
        """Get current user information"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError("User not found")

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "is_active": user.is_active,
            "is_super_admin": user.is_super_admin,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "company_id": str(user.company_id) if user.company_id else None,
            "role_name": user.role.name if user.role else None,
            "created_at": user.created_at.isoformat()
        }
