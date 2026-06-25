from __future__ import annotations

import contextvars
from uuid import UUID
from typing import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.companies.models import Company
from app.modules.frontend_api.defaults import ROLE_PERMISSIONS
from app.modules.frontend_api.utils import frontend_role
from app.modules.frontend_api.security_policy import client_ip_allowed, security_settings_for_user

_scope_override: contextvars.ContextVar[str | None] = contextvars.ContextVar("frontend_scope_override", default=None)


def get_scope_override() -> str | None:
    return _scope_override.get()


def _company_scope(company: Company) -> str:
    return f"tenant:{company.tenant_id}:company:{company.id}"


def get_selected_company_id(current_user) -> UUID | None:
    """Return the company selected for this request, including Super Admin impersonation."""
    selected = getattr(current_user, "_frontend_selected_company_id", None)
    if selected is not None:
        return selected if isinstance(selected, UUID) else UUID(str(selected))
    override = get_scope_override()
    if override and ":company:" in override:
        raw = override.rsplit(":company:", 1)[1]
        if raw not in {"none", "platform", "undefined"}:
            try:
                return UUID(raw)
            except ValueError:
                return None
    company_id = getattr(current_user, "company_id", None)
    if company_id is None:
        return None
    return company_id if isinstance(company_id, UUID) else UUID(str(company_id))


def get_frontend_user(
    request: Request,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Authenticate and validate the optional tenant/company selector headers.

    Normal users cannot escape their company. Super admins may select a real
    company with X-Company-ID; the corresponding tenant is verified before the
    frontend-state scope is changed for the request.
    """
    requested_company = request.headers.get("X-Company-ID")
    requested_tenant = request.headers.get("X-Tenant-ID")

    if getattr(current_user, "is_super_admin", False):
        if requested_company and requested_company not in {"platform", "none", "undefined"}:
            try:
                requested_company_id = UUID(requested_company)
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected company was not found") from exc
            company = db.query(Company).filter(Company.id == requested_company_id).first()
            if company is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected company was not found")
            if requested_tenant and requested_tenant not in {"platform", str(company.tenant_id)}:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant and company headers do not match")
            scope = _company_scope(company)
            _scope_override.set(scope)
            current_user._frontend_scope_key = scope
            current_user._frontend_selected_company_id = company.id
        else:
            _scope_override.set("platform")
            current_user._frontend_scope_key = "platform"
            current_user._frontend_selected_company_id = None
        return current_user

    own_company = str(getattr(current_user, "company_id", "") or "")
    own_tenant = str(getattr(current_user, "tenant_id", "") or "")
    if requested_company and requested_company not in {own_company, "none", "undefined"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company access denied")
    if requested_tenant and requested_tenant not in {own_tenant, "none", "undefined"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    scope = f"tenant:{own_tenant or 'none'}:company:{own_company or 'none'}"
    policy = security_settings_for_user(db, current_user)
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_ip = forwarded or (request.client.host if request.client else None)
    if not client_ip_allowed(client_ip, str(policy.get("allowedIpRanges") or "")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access is not allowed from this IP address")
    _scope_override.set(scope)
    current_user._frontend_scope_key = scope
    current_user._frontend_selected_company_id = getattr(current_user, "company_id", None)
    return current_user


def require_frontend_permission(permission: str) -> Callable:
    def checker(current_user=Depends(get_frontend_user)):
        role = frontend_role(current_user)
        if permission not in ROLE_PERMISSIONS.get(role, []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required",
            )
        return current_user
    return checker


def require_frontend_any_permission(*permissions: str) -> Callable:
    def checker(current_user=Depends(get_frontend_user)):
        role = frontend_role(current_user)
        allowed = ROLE_PERMISSIONS.get(role, [])
        if not any(permission in allowed for permission in permissions):
            joined = " or ".join(permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {joined} required",
            )
        return current_user
    return checker
