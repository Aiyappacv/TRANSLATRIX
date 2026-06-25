"""
FastAPI Dependency Injection
Common dependencies used across the application
"""
from typing import Optional, Generator
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.jwt import decode_token
from app.core.tenant_context import get_current_tenant_id, set_current_tenant_id
from app.modules.users.models import User
from app.modules.tenants.models import Tenant

# HTTP Bearer token authentication
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token
    Raises HTTPException if token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Import here to avoid circular imports
    from app.modules.users.repository import UserRepository

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Set tenant context for multi-tenancy
    if user.tenant_id:
        set_current_tenant_id(user.tenant_id)

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user
    Alias for get_current_user with explicit active check
    """
    return current_user


def get_current_super_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Verify current user is a super admin
    Raises HTTPException if user is not super admin
    """
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Optional[Tenant]:
    """
    Get current user's tenant
    Returns None if user is super admin without tenant
    """
    if current_user.tenant_id is None:
        return None

    from app.modules.tenants.repository import TenantRepository

    tenant_repo = TenantRepository(db)
    tenant = tenant_repo.get_by_id(current_user.tenant_id)

    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Tenant is {tenant.status}",
        )

    return tenant


def require_permission(permission: str):
    """
    Dependency factory to check user has specific permission

    Usage:
        @router.get("/endpoint", dependencies=[Depends(require_permission("entries:read"))])
    """
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        # Import here to avoid circular imports
        from app.core.permissions import user_has_permission

        if not user_has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required",
            )
        return current_user

    return permission_checker


def require_permissions(permissions: list[str]):
    """
    Decorator to check user has all specified permissions

    Usage:
        @router.get("/endpoint")
        @require_permissions(["entries:read", "entries:write"])
        async def my_endpoint(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func):
        from functools import wraps

        @wraps(func)
        async def wrapper(*args, current_user: User = None, **kwargs):
            # Import here to avoid circular imports
            from app.core.permissions import user_has_permission

            # Get current_user from kwargs if not passed directly
            if current_user is None:
                current_user = kwargs.get('current_user')

            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            # Check all permissions
            for permission in permissions:
                if not user_has_permission(current_user, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission} required",
                    )

            return await func(*args, current_user=current_user, **kwargs)

        return wrapper
    return decorator


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state
    Set by request ID middleware
    """
    return getattr(request.state, "request_id", "unknown")


def get_tenant_context(current_user: User = Depends(get_current_user)) -> UUID:
    """
    Get tenant context from current user

    Returns:
        Tenant ID of the current user

    Raises:
        HTTPException: If user has no tenant
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no associated tenant"
        )
    return current_user.tenant_id
