"""
User API Routes
User management and invitation endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.users.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserInvitationRequest,
    PasswordChangeRequest,
    UserStatusUpdate,
    RoleResponse
)
from app.modules.users.service import UserService
from app.modules.users.models import User
from app.core.response import success_response, error_response
from app.exceptions import TranslatrixException
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new user
    Requires authentication and proper permissions
    """
    try:
        service = UserService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        company_id = str(current_user.company_id) if current_user.company_id else None

        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required"
            )

        result = service.create_user(user_data, tenant_id, company_id)
        return success_response(
            data=result,
            message="User created successfully"
        )
    except TranslatrixException as e:
        logger.error("user_creation_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user by ID
    Returns user details with tenant isolation
    """
    try:
        service = UserService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.get_user(user_id, tenant_id)
        return result
    except TranslatrixException as e:
        logger.error("get_user_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.get("/company/{company_id}/users", response_model=UserListResponse)
async def list_company_users(
    company_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all users for a company
    Supports pagination
    """
    try:
        # Verify user has access to this company
        if not current_user.is_super_admin:
            if str(current_user.company_id) != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this company"
                )

        service = UserService(db)
        result = service.get_users_by_company(company_id, skip, limit)
        return result
    except TranslatrixException as e:
        logger.error("list_users_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user information
    Only accessible by admin or the user themselves
    """
    try:
        # Check permissions: user can update themselves, or admin can update anyone
        if str(current_user.id) != user_id and not current_user.is_super_admin:
            # Check if user is company admin
            if not current_user.role or current_user.role.name != "company_admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )

        service = UserService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        result = service.update_user(user_id, user_data, tenant_id)
        return success_response(
            data=result,
            message="User updated successfully"
        )
    except TranslatrixException as e:
        logger.error("update_user_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/{user_id}/change-password", response_model=dict)
async def change_password(
    user_id: str,
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change user password
    User can only change their own password
    """
    try:
        # Users can only change their own password
        if str(current_user.id) != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only change your own password"
            )

        service = UserService(db)
        result = service.change_password(user_id, password_data)
        return success_response(
            data=result,
            message="Password changed successfully"
        )
    except TranslatrixException as e:
        logger.error("change_password_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/{user_id}/status", response_model=dict)
async def update_user_status(
    user_id: str,
    status_data: UserStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user active status (activate/deactivate)
    Only accessible by admin
    """
    try:
        # Check if user is admin
        if not current_user.is_super_admin and (
            not current_user.role or current_user.role.name != "company_admin"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required"
            )

        service = UserService(db)
        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None

        from app.modules.users.schemas import UserUpdate
        update_data = UserUpdate(is_active=status_data.is_active)

        result = service.update_user(user_id, update_data, tenant_id)
        return success_response(
            data=result,
            message=f"User {'activated' if status_data.is_active else 'deactivated'} successfully"
        )
    except TranslatrixException as e:
        logger.error("update_user_status_failed", user_id=user_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.post("/invite", status_code=status.HTTP_201_CREATED, response_model=dict)
async def invite_user(
    invitation_data: UserInvitationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Invite a user to join the company
    Sends invitation email with secure token
    """
    try:
        # Check if user is admin
        if not current_user.is_super_admin and (
            not current_user.role or current_user.role.name not in ["company_admin", "company_finance_manager"]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or Finance Manager access required"
            )

        tenant_id = str(current_user.tenant_id) if current_user.tenant_id else None
        company_id = str(current_user.company_id) if current_user.company_id else None

        if not tenant_id or not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant and company context required"
            )

        service = UserService(db)
        result = service.invite_user(
            invitation_data,
            tenant_id,
            company_id,
            str(current_user.id)
        )
        return success_response(
            data=result,
            message="User invitation sent successfully"
        )
    except TranslatrixException as e:
        logger.error("invite_user_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/roles/", response_model=list[RoleResponse])
async def list_roles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List all available roles
    Accessible by authenticated users
    """
    try:
        service = UserService(db)
        result = service.get_all_roles()
        return result
    except TranslatrixException as e:
        logger.error("list_roles_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )


@router.get("/me/profile", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile
    Alias for /auth/me with full user details
    """
    try:
        service = UserService(db)
        result = service.get_user(str(current_user.id))
        return result
    except TranslatrixException as e:
        logger.error("get_profile_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message
        )


@router.put("/me/profile", response_model=dict)
async def update_my_profile(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update current user's profile
    Users can update their own profile information
    """
    try:
        service = UserService(db)
        # Remove role_id and is_active from update if user is not admin
        if not current_user.is_super_admin:
            user_data.role_id = None
            user_data.is_active = None

        result = service.update_user(str(current_user.id), user_data)
        return success_response(
            data=result,
            message="Profile updated successfully"
        )
    except TranslatrixException as e:
        logger.error("update_profile_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message
        )
