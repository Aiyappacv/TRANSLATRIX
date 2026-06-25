"""
RBAC Permissions System
Role-based access control for TRANSLATRIX PRO
"""
from typing import List, Set
from sqlalchemy.orm import Session


# Define all permissions in the system
class Permissions:
    """Central registry of all system permissions"""

    # Auth & User Management
    USERS_CREATE = "users:create"
    USERS_READ = "users:read"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"

    # Company Management
    COMPANIES_CREATE = "companies:create"
    COMPANIES_READ = "companies:read"
    COMPANIES_UPDATE = "companies:update"
    COMPANIES_DELETE = "companies:delete"

    # File & Ingestion
    FILES_UPLOAD = "files:upload"
    FILES_READ = "files:read"
    FILES_DELETE = "files:delete"
    FILES_PROCESS = "files:process"
    INGESTION_MANAGE = "ingestion:manage"

    # Entries & Classification
    ENTRIES_READ = "entries:read"
    ENTRIES_CREATE = "entries:create"
    ENTRIES_UPDATE = "entries:update"
    ENTRIES_DELETE = "entries:delete"
    ENTRIES_CLASSIFY = "entries:classify"

    # Review & Approval
    REVIEW_TASKS = "review:tasks"
    REVIEW_SUBMIT = "review:submit"
    APPROVE_ENTRIES = "approve:entries"
    APPROVE_FINAL = "approve:final"

    # SAP & Accounting
    SAP_CONFIG = "sap:config"
    SAP_POST = "sap:post"
    ACCOUNTING_CONFIG = "accounting:config"
    ACCOUNTING_POST = "accounting:post"

    # Mapping & Configuration
    MAPPING_READ = "mapping:read"
    MAPPING_CREATE = "mapping:create"
    MAPPING_UPDATE = "mapping:update"
    MAPPING_DELETE = "mapping:delete"

    # Validation Rules
    VALIDATION_READ = "validation:read"
    VALIDATION_MANAGE = "validation:manage"

    # Analytics & Audit
    ANALYTICS_VIEW = "analytics:view"
    AUDIT_VIEW = "audit:view"

    # Super Admin
    SUPER_ADMIN_ALL = "super_admin:all"
    SUPER_ADMIN_COMPANIES = "super_admin:companies"
    SUPER_ADMIN_USERS = "super_admin:users"
    SUPER_ADMIN_SYSTEM = "super_admin:system"


# Default role permissions
ROLE_PERMISSIONS = {
    "super_admin": [
        Permissions.SUPER_ADMIN_ALL,
        Permissions.SUPER_ADMIN_COMPANIES,
        Permissions.SUPER_ADMIN_USERS,
        Permissions.SUPER_ADMIN_SYSTEM,
    ],
    "company_admin": [
        Permissions.USERS_CREATE,
        Permissions.USERS_READ,
        Permissions.USERS_UPDATE,
        Permissions.COMPANIES_READ,
        Permissions.COMPANIES_UPDATE,
        Permissions.FILES_UPLOAD,
        Permissions.FILES_READ,
        Permissions.FILES_DELETE,
        Permissions.FILES_PROCESS,
        Permissions.INGESTION_MANAGE,
        Permissions.ENTRIES_READ,
        Permissions.ENTRIES_CREATE,
        Permissions.ENTRIES_UPDATE,
        Permissions.ENTRIES_DELETE,
        Permissions.APPROVE_FINAL,
        Permissions.SAP_CONFIG,
        Permissions.SAP_POST,
        Permissions.ACCOUNTING_CONFIG,
        Permissions.ACCOUNTING_POST,
        Permissions.MAPPING_READ,
        Permissions.MAPPING_CREATE,
        Permissions.MAPPING_UPDATE,
        Permissions.MAPPING_DELETE,
        Permissions.VALIDATION_MANAGE,
        Permissions.ANALYTICS_VIEW,
        Permissions.AUDIT_VIEW,
    ],
    "finance_manager": [
        Permissions.FILES_UPLOAD,
        Permissions.FILES_READ,
        Permissions.ENTRIES_READ,
        Permissions.ENTRIES_UPDATE,
        Permissions.ENTRIES_CLASSIFY,
        Permissions.REVIEW_TASKS,
        Permissions.APPROVE_ENTRIES,
        Permissions.SAP_POST,
        Permissions.ACCOUNTING_POST,
        Permissions.MAPPING_READ,
        Permissions.ANALYTICS_VIEW,
        Permissions.AUDIT_VIEW,
    ],
    "accountant": [
        Permissions.FILES_READ,
        Permissions.ENTRIES_READ,
        Permissions.ENTRIES_UPDATE,
        Permissions.REVIEW_TASKS,
        Permissions.REVIEW_SUBMIT,
        Permissions.MAPPING_READ,
        Permissions.ANALYTICS_VIEW,
    ],
    "reviewer": [
        Permissions.FILES_READ,
        Permissions.ENTRIES_READ,
        Permissions.REVIEW_TASKS,
        Permissions.REVIEW_SUBMIT,
    ],
    "viewer": [
        Permissions.FILES_READ,
        Permissions.ENTRIES_READ,
        Permissions.ANALYTICS_VIEW,
    ],
}


def get_role_permissions(role_name: str) -> Set[str]:
    """
    Get all permissions for a role

    Args:
        role_name: Name of the role

    Returns:
        Set of permission strings
    """
    return set(ROLE_PERMISSIONS.get(role_name, []))


def user_has_permission(user, permission: str) -> bool:
    """
    Check if user has a specific permission

    Args:
        user: User model instance
        permission: Permission string to check

    Returns:
        True if user has permission, False otherwise
    """
    # Super admin has all permissions
    if user.is_super_admin:
        return True

    # Get user's role permissions
    if not user.role:
        return False

    role_perms = get_role_permissions(user.role.name)

    return permission in role_perms


def user_has_any_permission(user, permissions: List[str]) -> bool:
    """
    Check if user has any of the specified permissions

    Args:
        user: User model instance
        permissions: List of permission strings

    Returns:
        True if user has at least one permission
    """
    return any(user_has_permission(user, perm) for perm in permissions)


def user_has_all_permissions(user, permissions: List[str]) -> bool:
    """
    Check if user has all specified permissions

    Args:
        user: User model instance
        permissions: List of permission strings

    Returns:
        True if user has all permissions
    """
    return all(user_has_permission(user, perm) for perm in permissions)
