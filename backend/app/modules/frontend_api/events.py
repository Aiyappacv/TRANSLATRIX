from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.modules.frontend_api.defaults import SECURITY_SETTINGS
from app.modules.frontend_api.store import get_state, set_state
from app.modules.frontend_api.utils import new_id, now_iso


def _retain(db: Session, scope: str, values: list[dict[str, Any]], timestamp_key: str) -> list[dict[str, Any]]:
    policy = {**SECURITY_SETTINGS, **get_state(db, scope, "security_settings", {})}
    retention_days = max(1, min(int(policy.get("auditRetentionDays") or 365), 3650))
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    retained: list[dict[str, Any]] = []
    for value in values[:10000]:
        raw = value.get(timestamp_key)
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            retained.append(value)
            continue
        if parsed >= cutoff:
            retained.append(value)
    return retained


def actor_name(user: Any) -> str:
    return str(getattr(user, "full_name", None) or getattr(user, "email", None) or "System")


def actor_role(user: Any) -> str:
    role = getattr(getattr(user, "role", None), "name", None)
    return str(role or ("super_admin" if getattr(user, "is_super_admin", False) else "system"))


def append_audit(
    db: Session,
    scope: str,
    user: Any,
    action: str,
    entity_type: str,
    entity_id: str,
    *,
    old_value: Any = None,
    new_value: Any = None,
    status: str = "success",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    timestamp = now_iso()
    event_id = new_id("audit")
    compact = {
        "id": event_id,
        "timestamp": timestamp,
        "actor": actor_name(user),
        "actorRole": actor_role(user),
        "action": action,
        "entityType": entity_type,
        "entityId": str(entity_id),
        "status": status,
        "oldValue": deepcopy(old_value),
        "newValue": deepcopy(new_value),
        "metadata": deepcopy(metadata or {}),
    }
    audit = get_state(db, scope, "audit", [])
    audit.insert(0, compact)
    set_state(db, scope, "audit", _retain(db, scope, audit, "timestamp"))

    detailed = {
        "id": event_id,
        "timestamp": timestamp,
        "user": actor_name(user),
        "action": action,
        "entityType": entity_type,
        "entityId": str(entity_id),
        "oldValue": deepcopy(old_value),
        "newValue": deepcopy(new_value),
        "ipAddress": "backend",
        "requestId": new_id("req"),
        "batchId": (metadata or {}).get("batchId"),
        "entryId": (metadata or {}).get("entryId"),
        "sapPostingId": (metadata or {}).get("sapPostingId"),
        "metadata": {"status": status, "role": actor_role(user), **deepcopy(metadata or {})},
    }
    logs = get_state(db, scope, "audit_logs", [])
    logs.insert(0, detailed)
    set_state(db, scope, "audit_logs", _retain(db, scope, logs, "timestamp"))
    return compact


def append_processing_log(
    db: Session,
    scope: str,
    *,
    stage: str,
    message: str,
    level: str = "info",
    job_id: str = "",
    file_id: str | None = None,
    batch_id: str | None = None,
    duration_ms: int | None = None,
    retry_count: int = 0,
) -> dict[str, Any]:
    item = {
        "id": new_id("processing"),
        "timestamp": now_iso(),
        "level": level,
        "stage": stage,
        "jobId": job_id or new_id("job"),
        "batchId": batch_id,
        "fileId": file_id,
        "message": message,
        "durationMs": duration_ms,
        "retryCount": retry_count,
        "requestId": new_id("req"),
    }
    values = get_state(db, scope, "processing_logs", [])
    values.insert(0, item)
    set_state(db, scope, "processing_logs", _retain(db, scope, values, "timestamp"))
    return item


def append_error(
    db: Session,
    scope: str,
    *,
    category: str,
    code: str,
    message: str,
    entity_type: str,
    entity_id: str,
    retryable: bool = True,
    severity: str = "high",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    item = {
        "id": new_id("error"),
        "category": category,
        "code": code,
        "message": message,
        "entityType": entity_type,
        "entityId": str(entity_id),
        "occurredAt": now_iso(),
        "retryable": retryable,
        "severity": severity,
        "attempts": 0,
        "requestId": new_id("req"),
        "details": deepcopy(details or {}),
    }
    values = get_state(db, scope, "errors", [])
    values.insert(0, item)
    set_state(db, scope, "errors", _retain(db, scope, values, "occurredAt"))
    return item
