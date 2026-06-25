from copy import deepcopy
from typing import Any
from sqlalchemy.orm import Session
from app.modules.frontend_api.models import FrontendState
from app.modules.frontend_api.security import get_scope_override


def scope_for_user(user) -> str:
    explicit_scope = getattr(user, "_frontend_scope_key", None)
    if explicit_scope:
        return explicit_scope
    override = get_scope_override()
    if override:
        return override
    if getattr(user, "is_super_admin", False):
        return "platform"
    tenant_id = str(getattr(user, "tenant_id", None) or "none")
    company_id = str(getattr(user, "company_id", None) or "none")
    return f"tenant:{tenant_id}:company:{company_id}"


def get_state(db: Session, scope_key: str, namespace: str, default: Any) -> Any:
    row = db.query(FrontendState).filter(
        FrontendState.scope_key == scope_key,
        FrontendState.namespace == namespace,
    ).first()
    if row is None:
        row = FrontendState(scope_key=scope_key, namespace=namespace, payload=deepcopy(default))
        db.add(row)
        db.commit()
        db.refresh(row)
    return deepcopy(row.payload)


def set_state(db: Session, scope_key: str, namespace: str, value: Any) -> Any:
    row = db.query(FrontendState).filter(
        FrontendState.scope_key == scope_key,
        FrontendState.namespace == namespace,
    ).first()
    if row is None:
        row = FrontendState(scope_key=scope_key, namespace=namespace, payload=deepcopy(value))
        db.add(row)
    else:
        row.payload = deepcopy(value)
    db.commit()
    db.refresh(row)
    return deepcopy(row.payload)


def append_state(db: Session, scope_key: str, namespace: str, item: Any, default: list | None = None, prepend: bool = True) -> list:
    values = get_state(db, scope_key, namespace, default or [])
    if prepend:
        values.insert(0, deepcopy(item))
    else:
        values.append(deepcopy(item))
    return set_state(db, scope_key, namespace, values)
