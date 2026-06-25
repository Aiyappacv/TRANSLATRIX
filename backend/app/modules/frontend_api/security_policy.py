from __future__ import annotations

import ipaddress
import re
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.modules.frontend_api.defaults import SECURITY_SETTINGS


def scope_for_identity(user: Any) -> str:
    tenant_id = getattr(user, "tenant_id", None)
    company_id = getattr(user, "company_id", None)
    if company_id:
        return f"tenant:{tenant_id or 'none'}:company:{company_id}"
    return "platform"


def security_settings_for_user(db: Session, user: Any) -> dict[str, Any]:
    from app.modules.frontend_api.store import get_state
    if getattr(user, "is_super_admin", False) or not getattr(user, "company_id", None):
        return dict(SECURITY_SETTINGS)
    return {**SECURITY_SETTINGS, **get_state(db, scope_for_identity(user), "security_settings", {})}


def validate_password_against_policy(password: str, policy: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    minimum = max(8, min(int(policy.get("passwordMinimumLength") or 8), 72))
    if len(password) < minimum:
        errors.append(f"Password must be at least {minimum} characters.")
    if policy.get("passwordRequireUppercase") and not any(character.isupper() for character in password):
        errors.append("Password must contain an uppercase letter.")
    if policy.get("passwordRequireLowercase") and not any(character.islower() for character in password):
        errors.append("Password must contain a lowercase letter.")
    if policy.get("passwordRequireNumber") and not any(character.isdigit() for character in password):
        errors.append("Password must contain a number.")
    if policy.get("passwordRequireSymbol") and not re.search(r"[^A-Za-z0-9]", password):
        errors.append("Password must contain a symbol.")
    return errors


def password_is_expired(user: Any, policy: dict[str, Any]) -> bool:
    expiry_days = int(policy.get("passwordExpiryDays") or 0)
    if expiry_days <= 0:
        return False
    changed_at = getattr(user, "password_changed_at", None) or getattr(user, "created_at", None)
    if changed_at is None:
        return True
    if changed_at.tzinfo is None:
        changed_at = changed_at.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - changed_at).days >= expiry_days


def client_ip_allowed(client_ip: str | None, allowed_ranges: str | None) -> bool:
    configured = [value.strip() for value in re.split(r"[,\n;]+", allowed_ranges or "") if value.strip()]
    if not configured:
        return True
    if not client_ip:
        return False
    try:
        address = ipaddress.ip_address(client_ip)
    except ValueError:
        return False
    for value in configured:
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError:
            try:
                if address == ipaddress.ip_address(value):
                    return True
            except ValueError:
                continue
        else:
            if address in network:
                return True
    return False
