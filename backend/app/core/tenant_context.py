"""
Tenant Context Management
Thread-local storage for current tenant ID to enforce multi-tenancy
"""
import contextvars
from typing import Optional
from uuid import UUID

# Context variable to store current tenant ID per request
_current_tenant_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def set_current_tenant_id(tenant_id: str | UUID) -> None:
    """
    Set the current tenant ID for this request context

    Args:
        tenant_id: Tenant ID to set
    """
    if isinstance(tenant_id, UUID):
        tenant_id = str(tenant_id)
    _current_tenant_id.set(tenant_id)


def get_current_tenant_id() -> Optional[str]:
    """
    Get the current tenant ID from request context

    Returns:
        Current tenant ID or None if not set
    """
    return _current_tenant_id.get()


def clear_current_tenant_id() -> None:
    """Clear the current tenant ID from context"""
    _current_tenant_id.set(None)


def ensure_tenant_context() -> str:
    """
    Ensure tenant context is set

    Returns:
        Current tenant ID

    Raises:
        ValueError: If no tenant context is set
    """
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        raise ValueError("No tenant context set for this request")
    return tenant_id
