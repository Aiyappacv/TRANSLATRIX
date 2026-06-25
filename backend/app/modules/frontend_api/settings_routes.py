from copy import deepcopy
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.defaults import APPROVAL_RULES, OCR_SETTINGS, SECURITY_SETTINGS
from app.modules.frontend_api.events import append_audit
from app.modules.frontend_api.store import get_state, scope_for_user, set_state

router = APIRouter()


def _merge(default, stored):
    if isinstance(default, dict):
        value = deepcopy(default)
        if isinstance(stored, dict):
            value.update(stored)
        return value
    return stored if stored is not None else deepcopy(default)


def _normalize(namespace: str, value):
    if namespace == "ocr_settings":
        value["confidenceThreshold"] = min(100, max(0, int(value.get("confidenceThreshold", 80))))
        value["maxPagesPerFile"] = max(1, int(value.get("maxPagesPerFile", 500)))
    elif namespace == "security_settings":
        value["passwordMinimumLength"] = min(128, max(8, int(value.get("passwordMinimumLength", 12))))
        value["sessionTimeoutMinutes"] = max(5, int(value.get("sessionTimeoutMinutes", 30)))
        value["passwordExpiryDays"] = max(0, int(value.get("passwordExpiryDays", 0)))
        value["auditRetentionDays"] = max(30, int(value.get("auditRetentionDays", 365)))
        if value.get("ssoEnabled") and not str(value.get("ssoProvider") or "").strip():
            raise HTTPException(status_code=422, detail="SSO provider is required when SSO is enabled")
    return value


def settings_get(namespace: str, default):
    def endpoint(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        scope = scope_for_user(current_user)
        stored = get_state(db, scope, namespace, None)
        value = _normalize(namespace, _merge(default, stored))
        if stored != value:
            set_state(db, scope, namespace, value)
        return value
    return endpoint


def settings_put(namespace: str, default=None):
    def endpoint(payload=Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
        scope = scope_for_user(current_user)
        previous = get_state(db, scope, namespace, deepcopy(default))
        value = _normalize(namespace, _merge(default, payload) if default is not None else payload)
        result = set_state(db, scope, namespace, value)
        append_audit(db, scope, current_user, "SETTINGS_UPDATED", "settings", namespace, old_value=previous, new_value=value)
        return result
    return endpoint

router.add_api_route("/settings/mapping-rules", settings_get("sap_mappings", []), methods=["GET"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/sap-tcode-mappings", settings_put("sap_mappings", []), methods=["PUT"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/gl-account-mappings", settings_get("gl_mappings", []), methods=["GET"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/gl-account-mappings", settings_put("gl_mappings", []), methods=["PUT"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/approval-rules", settings_get("approval_rules", APPROVAL_RULES), methods=["GET"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/approval-rules", settings_put("approval_rules", APPROVAL_RULES), methods=["PUT"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/ocr", settings_get("ocr_settings", OCR_SETTINGS), methods=["GET"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/ocr", settings_put("ocr_settings", OCR_SETTINGS), methods=["PUT"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/security", settings_get("security_settings", SECURITY_SETTINGS), methods=["GET"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
router.add_api_route("/settings/security", settings_put("security_settings", SECURITY_SETTINGS), methods=["PUT"], dependencies=[Depends(require_frontend_permission("settings:manage"))])
