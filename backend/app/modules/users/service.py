"""
User Service
Business logic for user management
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from uuid import UUID
import structlog
from datetime import datetime

from app.modules.users.repository import UserRepository, RoleRepository
from app.modules.users.schemas import UserCreate, UserUpdate, UserInvitationRequest, PasswordChangeRequest
from app.core.security import hash_password, verify_password, validate_password_strength
from app.exceptions import (
    UserNotFoundError,
    DuplicateEntryError,
    ValidationError,
    AuthorizationError,
    AuthenticationError
)

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user operations"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def create_user(
        self,
        user_data: UserCreate,
        tenant_id: str,
        company_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new user

        Args:
            user_data: User creation data
            tenant_id: Tenant UUID
            company_id: Optional company UUID

        Returns:
            Created user information

        Raises:
            DuplicateEntryError: If email already exists
            ValidationError: If validation fails
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(user_data.password)
        if not is_valid:
            raise ValidationError(error_msg)

        # Check if email already exists
        existing_user = self.user_repo.get_by_email(user_data.email)
        if existing_user:
            logger.warning("duplicate_user_email", email=user_data.email)
            raise DuplicateEntryError(f"User with email '{user_data.email}' already exists")

        # Validate role if provided
        if user_data.role_id:
            role = self.role_repo.get_by_id(user_data.role_id)
            if not role:
                raise ValidationError("Invalid role ID")

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user
        user = self.user_repo.create(
            email=user_data.email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            company_id=company_id or user_data.company_id,
            role_id=user_data.role_id,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            job_title=user_data.job_title,
            department=user_data.department,
            is_active=user_data.is_active
        )

        logger.info(
            "user_created",
            user_id=str(user.id),
            email=user.email,
            tenant_id=tenant_id
        )

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        }

    def get_user(self, user_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user by ID

        Args:
            user_id: User UUID
            tenant_id: Optional tenant ID for authorization check

        Returns:
            User information

        Raises:
            UserNotFoundError: If user not found
            AuthorizationError: If user doesn't belong to tenant
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning("user_not_found", user_id=user_id)
            raise UserNotFoundError("User not found")

        # Tenant isolation check
        if tenant_id and user.tenant_id and str(user.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_user_access",
                user_id=user_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this user")

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "job_title": user.job_title,
            "department": user.department,
            "tenant_id": str(user.tenant_id) if user.tenant_id else None,
            "company_id": str(user.company_id) if user.company_id else None,
            "role_id": str(user.role_id) if user.role_id else None,
            "role_name": user.role.name if user.role else None,
            "is_active": user.is_active,
            "is_super_admin": user.is_super_admin,
            "is_email_verified": user.is_email_verified,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat()
        }

    def get_users_by_company(
        self,
        company_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get all users for a company

        Args:
            company_id: Company UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Paginated list of users
        """
        users = self.user_repo.get_by_company_id(company_id)
        total = len(users)

        # Manual pagination
        paginated_users = users[skip:skip + limit]

        total_pages = (total + limit - 1) // limit if limit > 0 else 1
        current_page = (skip // limit) + 1 if limit > 0 else 1

        return {
            "items": [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "first_name": u.first_name,
                    "last_name": u.last_name,
                    "role_name": u.role.name if u.role else None,
                    "is_active": u.is_active,
                    "created_at": u.created_at.isoformat()
                }
                for u in paginated_users
            ],
            "total": total,
            "page": current_page,
            "page_size": limit,
            "total_pages": total_pages
        }

    def update_user(
        self,
        user_id: str,
        user_data: UserUpdate,
        tenant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user information

        Args:
            user_id: User UUID
            user_data: User update data
            tenant_id: Optional tenant ID for authorization check

        Returns:
            Updated user information

        Raises:
            UserNotFoundError: If user not found
            AuthorizationError: If user doesn't belong to tenant
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning("user_not_found", user_id=user_id)
            raise UserNotFoundError("User not found")

        # Tenant isolation check
        if tenant_id and user.tenant_id and str(user.tenant_id) != tenant_id:
            logger.warning(
                "unauthorized_user_access",
                user_id=user_id,
                tenant_id=tenant_id
            )
            raise AuthorizationError("Access denied to this user")

        # Validate role if being updated
        if user_data.role_id:
            role = self.role_repo.get_by_id(user_data.role_id)
            if not role:
                raise ValidationError("Invalid role ID")

        # Update user with only provided fields
        update_data = user_data.model_dump(exclude_unset=True)
        user = self.user_repo.update(user_id, **update_data)

        logger.info("user_updated", user_id=user_id)

        return {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "updated_at": user.updated_at.isoformat()
        }

    def change_password(
        self,
        user_id: str,
        password_data: PasswordChangeRequest
    ) -> Dict[str, Any]:
        """
        Change user password

        Args:
            user_id: User UUID
            password_data: Password change data

        Returns:
            Success message

        Raises:
            UserNotFoundError: If user not found
            AuthenticationError: If current password is incorrect
            ValidationError: If new password doesn't meet requirements
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            logger.warning("user_not_found", user_id=user_id)
            raise UserNotFoundError("User not found")

        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            logger.warning("incorrect_current_password", user_id=user_id)
            raise AuthenticationError("Current password is incorrect")

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(password_data.new_password)
        if not is_valid:
            raise ValidationError(error_msg)

        # Update password
        hashed_password = hash_password(password_data.new_password)
        self.user_repo.update_password(user_id, hashed_password)

        logger.info("password_changed", user_id=user_id)

        return {
            "message": "Password changed successfully",
            "user_id": user_id
        }

    def invite_user(
        self,
        invitation_data: UserInvitationRequest,
        tenant_id: str,
        company_id: str,
        invited_by_user_id: str
    ) -> Dict[str, Any]:
        """
        Invite a user to join the company

        Args:
            invitation_data: User invitation data
            tenant_id: Tenant UUID
            company_id: Company UUID
            invited_by_user_id: UUID of user sending invitation

        Returns:
            Invitation details

        Raises:
            DuplicateEntryError: If email already exists
            ValidationError: If validation fails
        """
        # Check if email already exists
        existing_user = self.user_repo.get_by_email(invitation_data.email)
        if existing_user:
            logger.warning("duplicate_user_email", email=invitation_data.email)
            raise DuplicateEntryError(f"User with email '{invitation_data.email}' already exists")

        # Validate role
        role = self.role_repo.get_by_id(invitation_data.role_id)
        if not role:
            raise ValidationError("Invalid role ID")

        # In production, create invitation token and send email
        # For now, we'll create the user with a temporary password
        # and mark as not verified

        # Generate a secure temporary password
        import secrets
        import string
        temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
        hashed_password = hash_password(temp_password)

        user = self.user_repo.create(
            email=invitation_data.email,
            hashed_password=hashed_password,
            tenant_id=tenant_id,
            company_id=company_id,
            role_id=invitation_data.role_id,
            first_name=invitation_data.first_name,
            last_name=invitation_data.last_name,
            job_title=invitation_data.job_title,
            department=invitation_data.department,
            is_active=False,  # Will be activated when they accept invitation
            is_email_verified=False
        )

        logger.info(
            "user_invited",
            user_id=str(user.id),
            email=user.email,
            invited_by=invited_by_user_id
        )

        return {
            "message": "User invitation sent successfully",
            "user_id": str(user.id),
            "email": user.email,
            "note": "In production, an invitation email would be sent with a secure token"
        }

    def get_all_roles(self) -> List[Dict[str, Any]]:
        """
        Get all available roles

        Returns:
            List of roles
        """
        roles = self.role_repo.get_all()

        return [
            {
                "id": str(r.id),
                "name": r.name,
                "display_name": r.display_name,
                "description": r.description,
                "is_system_role": r.is_system_role
            }
            for r in roles
        ]
