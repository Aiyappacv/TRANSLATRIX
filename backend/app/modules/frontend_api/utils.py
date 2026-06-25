import hashlib
import hmac
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import HTTPException, status
from app.config import settings
from app.modules.frontend_api.defaults import BACKEND_ROLE_TO_FRONTEND, ROLE_PERMISSIONS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "upload.bin"


def frontend_role(user) -> str:
    if getattr(user, "is_super_admin", False):
        return "spectra_super_admin"
    role_name = getattr(getattr(user, "role", None), "name", "read_only")
    return BACKEND_ROLE_TO_FRONTEND.get(role_name, "read_only")


def user_dto(user, mfa_enabled: bool = False) -> dict[str, Any]:
    role = frontend_role(user)
    company = getattr(user, "company", None)
    tenant_id = str(getattr(user, "tenant_id", None) or "platform")
    company_id = str(getattr(user, "company_id", None) or "platform")
    company_name = getattr(company, "legal_name", None) or ("TRANSLATRIX PRO Platform" if role == "spectra_super_admin" else "Company")
    return {
        "id": str(user.id),
        "name": getattr(user, "full_name", None) or user.email,
        "email": user.email,
        "tenantId": tenant_id,
        "companyId": company_id,
        "companyName": company_name,
        "roles": [role],
        "permissions": ROLE_PERMISSIONS.get(role, []),
        "mfaEnabled": bool(mfa_enabled),
        "isPlatformOwner": role == "spectra_super_admin",
        "canSwitchCompanies": role == "spectra_super_admin",
    }


def company_dto(company, status_value: str = "active") -> dict[str, Any]:
    return {
        "id": str(company.id),
        "tenantId": str(company.tenant_id),
        "legalName": company.legal_name,
        "tradingName": company.trading_name or "",
        "country": company.country,
        "industry": company.industry or "",
        "registrationNumber": company.registration_number or "",
        "taxId": company.tax_number or company.vat_number or company.gst_number or "",
        "defaultCurrency": company.default_currency or "USD",
        "defaultCompanyCode": "",
        "fiscalYearVariant": company.fiscal_year_start or "",
        "financeContact": company.email,
        "status": status_value,
        "companyAdminEmail": company.email,
        "plan": "Starter",
        "tokenLimit": 0,
        "tokenUsage": 0,
    }


def company_user_dto(user) -> dict[str, Any]:
    role = frontend_role(user)
    company = getattr(user, "company", None)
    return {
        "id": str(user.id),
        "companyId": str(user.company_id or ""),
        "companyName": getattr(company, "legal_name", "") or "",
        "name": getattr(user, "full_name", None) or user.email,
        "email": user.email,
        "role": role,
        "department": user.department or "",
        "approvalLimit": 0,
        "status": "active" if user.is_active else "disabled",
    }


def require_item(items: list[dict], item_id: str, key: str = "id") -> dict:
    item = next((value for value in items if str(value.get(key)) == str(item_id)), None)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return item


def preview_token(file_id: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), file_id.encode(), hashlib.sha256).hexdigest()


def validate_preview_token(file_id: str, token: str) -> None:
    if not hmac.compare_digest(preview_token(file_id), token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid preview token")
