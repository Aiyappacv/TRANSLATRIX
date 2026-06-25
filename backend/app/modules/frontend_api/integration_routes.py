from __future__ import annotations

import csv
import io
import json
import os
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape

import httpx

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.frontend_api.defaults import PROVIDERS, SAP_SETTINGS, provider_detail
from app.modules.frontend_api.events import append_audit, append_error, append_processing_log
from app.modules.frontend_api.finance_routes import ensure_entries
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, set_state, scope_for_user
from app.modules.frontend_api.utils import new_id, now_iso, require_item, safe_filename

router = APIRouter()
EXPORT_ROOT = Path(getattr(settings, "FRONTEND_UPLOAD_DIR", "/app/data/uploads")) / "exports"
SECRET_FIELDS = {"clientSecret", "apiKey", "password", "accessToken", "refreshToken", "username"}


def _extract_secrets(payload: dict) -> dict:
    return {key: str(value) for key, value in payload.items() if key in SECRET_FIELDS and value not in (None, "", "********")}


def _save_secrets(db: Session, scope: str, key: str, payload: dict) -> dict:
    secrets_by_provider = get_state(db, scope, "integration_secrets", {})
    current = dict(secrets_by_provider.get(key) or {})
    current.update(_extract_secrets(payload))
    secrets_by_provider[key] = current
    set_state(db, scope, "integration_secrets", secrets_by_provider)
    return current


def _safe_settings(payload: dict) -> dict:
    return {key: (None if key in SECRET_FIELDS else value) for key, value in payload.items()}


def _probe_connection(base_url: str, auth_type: str, secrets_value: dict, timeout_seconds: int = 8) -> tuple[bool, int, str, str | None]:
    if base_url.startswith("mock://") and settings.APP_ENV != "production":
        return True, 1, "Development simulation endpoint accepted.", "development-simulation"
    if not base_url.startswith(("http://", "https://")):
        return False, 0, "A valid HTTPS service endpoint is required.", None
    headers = {"Accept": "application/json", "User-Agent": "TRANSLATRIX-PRO/1.0"}
    auth = None
    if auth_type in {"basic", "basic_auth"}:
        username = secrets_value.get("username")
        password = secrets_value.get("password")
        if not username or not password:
            return False, 0, "Username and password are required for basic authentication.", None
        auth = (username, password)
    elif auth_type in {"bearer", "token", "oauth2"} and secrets_value.get("accessToken"):
        headers["Authorization"] = f"Bearer {secrets_value['accessToken']}"
    started = datetime.now(timezone.utc)
    try:
        response = httpx.get(base_url, headers=headers, auth=auth, timeout=max(2, min(timeout_seconds, 30)), follow_redirects=True)
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        if response.status_code >= 400:
            return False, latency, f"Provider responded with HTTP {response.status_code}.", response.headers.get("server")
        return True, latency, f"Provider responded with HTTP {response.status_code}.", response.headers.get("server")
    except Exception as exc:
        latency = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return False, latency, f"Connection failed: {exc}", None


def _accounting_payload(entry: dict, user) -> dict:
    accounting = entry.get("accountingEntry") or {}
    lines = []
    for line in accounting.get("debitLines", []):
        lines.append({"type": "GL", "account": line.get("glAccount", ""), "debit": float(line.get("amount") or 0), "credit": 0, "costCenter": line.get("costCenter")})
    for line in accounting.get("creditLines", []):
        lines.append({"type": "GL", "account": line.get("glAccount", ""), "debit": 0, "credit": float(line.get("amount") or 0), "costCenter": line.get("costCenter")})
    header = accounting.get("header") or {}
    return {
        "tenant_id": str(getattr(user, "tenant_id", "") or ""),
        "company_id": str(getattr(user, "company_id", "") or ""),
        "entry_id": entry.get("id", ""),
        "category": entry.get("category", ""),
        "posting_type": entry.get("postingProcess", ""),
        "header": {"posting_date": header.get("postingDate") or entry.get("date"), "document_date": header.get("documentDate") or entry.get("date"), "currency": entry.get("currency"), "reference": entry.get("reference")},
        "parties": {"vendor_code": entry.get("vendor"), "customer_code": entry.get("customer")},
        "lines": lines,
    }


def _eligible(entry: dict) -> bool:
    return entry.get("status") == "approved" and entry.get("validationStatus") == "valid" and not any(issue.get("severity") == "error" for issue in entry.get("issues", []))


def ensure_postings(db: Session, scope: str, user) -> list[dict]:
    entries = ensure_entries(db, scope)
    existing = get_state(db, scope, "sap_postings", [])
    by_entry = {str(record.get("entryId")): record for record in existing}
    records: list[dict] = []
    for entry in entries:
        if not _eligible(entry):
            continue
        entry_id = str(entry.get("id"))
        record = by_entry.get(entry_id)
        if record is None:
            record = {
                "id": new_id("sap"), "entryId": entry_id, "category": entry.get("category"), "sapTCode": entry.get("sapTCode"),
                "sapProcess": entry.get("postingProcess"), "companyCode": ((entry.get("accountingEntry") or {}).get("header") or {}).get("companyCode", ""),
                "amount": entry.get("amount", 0), "currency": entry.get("currency"), "approvalStatus": "approved", "sapStatus": "ready", "attempts": 0,
                "payload": _accounting_payload(entry, user), "accountingLines": ((entry.get("accountingEntry") or {}).get("debitLines") or []) + ((entry.get("accountingEntry") or {}).get("creditLines") or []),
                "sourceEntry": deepcopy(entry),
                "timeline": [{"id": new_id("timeline"), "timestamp": now_iso(), "title": "Posting record created", "description": "Entry is approved, validated, and ready after SAP connection validation.", "status": "current", "actor": "System"}],
                "auditEvents": [],
            }
        else:
            record.update({"approvalStatus": "approved", "sourceEntry": deepcopy(entry), "payload": _accounting_payload(entry, user), "amount": entry.get("amount", 0), "currency": entry.get("currency")})
            if record.get("sapStatus") not in {"posted", "failed"}:
                record["sapStatus"] = "ready"
        records.append(record)
    set_state(db, scope, "sap_postings", records)
    return records


@router.get("/posting/payload/{entry_id}", dependencies=[Depends(require_frontend_permission("posting:read"))])
def posting_payload(entry_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    entry = require_item(ensure_entries(db, scope_for_user(current_user)), entry_id)
    return _accounting_payload(entry, current_user)


@router.post("/posting/{entry_id}", dependencies=[Depends(require_frontend_permission("posting:execute"))])
def generic_post(entry_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    records = ensure_postings(db, scope, current_user)
    record = next((item for item in records if item.get("entryId") == entry_id or item.get("id") == entry_id), None)
    if not record:
        raise HTTPException(status_code=422, detail="Only approved and validated entries can be posted.")
    return _execute(record, records, db, scope, current_user, "generic")


def _execute(record: dict, records: list[dict], db: Session, scope: str, current_user, provider: str = "sap"):
    entry = require_item(ensure_entries(db, scope), str(record.get("entryId")))
    if not _eligible(entry):
        raise HTTPException(status_code=422, detail="Posting is blocked until the entry is approved and validation is successful.")
    sap_settings = get_state(db, scope, "sap_settings", deepcopy(SAP_SETTINGS))
    if not sap_settings.get("baseUrl") or sap_settings.get("status") != "connected":
        raise HTTPException(status_code=422, detail="Configure SAP and complete a successful connection test before posting.")

    record["attempts"] = int(record.get("attempts") or 0) + 1
    record["lastAttemptAt"] = now_iso()
    try:
        base_url = str(sap_settings.get("baseUrl") or "")
        simulated = base_url.startswith("mock://") and settings.APP_ENV != "production"
        response_payload: dict = {}
        http_status = 200
        if simulated:
            document_number = f"DEV{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
            response_message = "Development SAP simulation completed the posting."
        else:
            if not base_url.startswith(("http://", "https://")):
                raise ValueError("SAP posting requires a valid HTTPS posting endpoint.")
            secrets_value = get_state(db, scope, "integration_secrets", {}).get("sap_s4hana", {})
            headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": "TRANSLATRIX-PRO/1.0"}
            auth = None
            auth_type = str(sap_settings.get("authType") or "").lower()
            if auth_type in {"basic", "basic_auth"}:
                if not secrets_value.get("username") or not secrets_value.get("password"):
                    raise ValueError("SAP username and password are required for basic authentication.")
                auth = (secrets_value["username"], secrets_value["password"])
            elif secrets_value.get("accessToken"):
                headers["Authorization"] = f"Bearer {secrets_value['accessToken']}"
            live_response = httpx.post(base_url, headers=headers, auth=auth, json=record.get("payload") or {}, timeout=max(5, min(int(sap_settings.get("requestTimeoutSeconds") or 60), 120)), follow_redirects=True)
            http_status = live_response.status_code
            if live_response.status_code >= 400:
                raise ValueError(f"SAP posting failed with HTTP {live_response.status_code}: {live_response.text[:500]}")
            try:
                response_payload = live_response.json() if live_response.content else {}
            except ValueError:
                response_payload = {"rawResponse": live_response.text[:2000]}
            document_number = str(response_payload.get("sapDocumentNumber") or response_payload.get("documentNumber") or response_payload.get("AccountingDocument") or response_payload.get("id") or "")
            if not document_number:
                document_number = f"SAP{datetime.now(timezone.utc):%Y%m%d%H%M%S}"
            response_message = "SAP endpoint accepted the posting."
        record["sapStatus"] = "posted"
        record["sapDocumentNumber"] = document_number
        record["fiscalYear"] = str(response_payload.get("fiscalYear") or datetime.now(timezone.utc).year)
        record["approvedAt"] = now_iso()
        record["approvedBy"] = getattr(current_user, "full_name", None) or getattr(current_user, "email", "User")
        response = {"success": True, "simulated": simulated, "httpStatus": http_status, "requestId": new_id("req"), "sapDocumentNumber": record["sapDocumentNumber"], "fiscalYear": record["fiscalYear"], "companyCode": record.get("companyCode"), "message": response_message, "providerResponse": response_payload}
        record["response"] = response
        record.setdefault("timeline", []).append({"id": new_id("timeline"), "timestamp": now_iso(), "title": "Posting completed", "description": response["message"], "status": "completed", "actor": record["approvedBy"]})
        set_state(db, scope, "sap_postings", records)
        entries = ensure_entries(db, scope)
        source = require_item(entries, str(record.get("entryId")))
        source["status"] = "sap_posted"
        source["updatedAt"] = now_iso()
        set_state(db, scope, "entries", entries)
        result = {"id": new_id("result"), "entryId": record.get("entryId"), "providerCode": provider, "externalDocumentNumber": record.get("sapDocumentNumber"), "fiscalYear": record.get("fiscalYear"), "companyCode": record.get("companyCode"), "status": "posted", "postedAt": now_iso()}
        results = get_state(db, scope, "posting_results", [])
        results.insert(0, result)
        set_state(db, scope, "posting_results", results)
        append_processing_log(db, scope, stage="sap_posting", message=f"Entry {entry.get('entryId')} posted successfully", level="success", job_id=record["id"], file_id=entry.get("fileId"))
        append_audit(db, scope, current_user, "SAP_POSTED", "posting", record["id"], new_value=result, metadata={"entryId": entry.get("entryId"), "sapPostingId": record["id"]})
        return record
    except HTTPException:
        raise
    except Exception as exc:
        record["sapStatus"] = "failed"
        record["errorCode"] = "SAP_POST_FAILED"
        record["errorMessage"] = str(exc)
        set_state(db, scope, "sap_postings", records)
        append_error(db, scope, category="sap_posting", code="SAP_POST_FAILED", message=str(exc), entity_type="posting", entity_id=record["id"], retryable=True, details={"entryId": entry.get("entryId")})
        append_audit(db, scope, current_user, "SAP_POST_FAILED", "posting", record["id"], status="failed", new_value={"error": str(exc)}, metadata={"entryId": entry.get("entryId"), "sapPostingId": record["id"]})
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/settings/sap-tcode-mappings", dependencies=[Depends(require_frontend_permission("posting:read"))])
def sap_tcodes(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "sap_tcode_mappings", [])


@router.get("/posting/results", dependencies=[Depends(require_frontend_permission("posting:read"))])
def posting_results(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "posting_results", [])


@router.get("/posting/sap", dependencies=[Depends(require_frontend_permission("posting:read"))])
def list_sap(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ensure_postings(db, scope_for_user(current_user), current_user)


@router.get("/posting/sap/configuration-status", dependencies=[Depends(require_frontend_permission("posting:read"))])
def sap_configuration_status(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Expose only posting readiness, without leaking integration credentials."""
    sap = get_state(db, scope_for_user(current_user), "sap_settings", deepcopy(SAP_SETTINGS))
    connected = sap.get("status") == "connected" and bool(str(sap.get("baseUrl") or "").strip())
    if connected:
        message = "SAP is configured and the latest connection test succeeded."
    elif sap.get("status") in {"failed", "degraded"}:
        message = "SAP posting is disabled because the latest connection test failed. Ask an Integration Manager to correct and retest the connection."
    else:
        message = "SAP posting is disabled because SAP is not configured. Ask an Integration Manager to configure and test the connection."
    return {
        "status": sap.get("status") or "not_configured",
        "canPost": connected,
        "message": message,
        "lastTestedAt": sap.get("lastTestedAt"),
    }


@router.get("/posting/sap/{posting_id}", dependencies=[Depends(require_frontend_permission("posting:read"))])
def get_sap(posting_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return require_item(ensure_postings(db, scope_for_user(current_user), current_user), posting_id)


@router.post("/posting/sap/{posting_id}/execute", dependencies=[Depends(require_frontend_permission("posting:execute"))])
def execute_sap(posting_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    records = ensure_postings(db, scope, current_user)
    return _execute(require_item(records, posting_id), records, db, scope, current_user)


@router.post("/posting/sap/{posting_id}/retry", dependencies=[Depends(require_frontend_permission("posting:retry"))])
def retry_sap(posting_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    records = ensure_postings(db, scope, current_user)
    return _execute(require_item(records, posting_id), records, db, scope, current_user)


@router.get("/integrations/sap/settings", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def get_sap_settings(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "sap_settings", deepcopy(SAP_SETTINGS))


@router.put("/integrations/sap/settings", dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def put_sap_settings(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    _save_secrets(db, scope, "sap_s4hana", payload)
    value = {**deepcopy(SAP_SETTINGS), **_safe_settings(payload), "updatedAt": now_iso()}
    if not value.get("baseUrl"):
        value["status"] = "not_configured"
    set_state(db, scope, "sap_settings", value)
    append_audit(db, scope, current_user, "SAP_SETTINGS_UPDATED", "integration", "sap_s4hana", new_value={key: value.get(key) for key in ("systemName", "environment", "baseUrl", "companyCode", "status")})
    return value


@router.post("/integrations/sap/test", dependencies=[Depends(require_frontend_permission("integrations:test"))])
def test_sap(payload: dict | None = Body(None), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    submitted = payload or {}
    saved_secrets = _save_secrets(db, scope, "sap_s4hana", submitted)
    current = get_state(db, scope, "sap_settings", deepcopy(SAP_SETTINGS))
    candidate = {**current, **_safe_settings(submitted)}
    base_url = str(candidate.get("baseUrl") or "")
    ok, latency, message, system_version = _probe_connection(base_url, str(candidate.get("authType") or ""), saved_secrets, int(candidate.get("requestTimeoutSeconds") or 8))
    current.update(candidate)
    current.update({"status": "connected" if ok else ("failed" if base_url else "not_configured"), "lastTestedAt": now_iso(), "lastTestLatencyMs": latency})
    set_state(db, scope, "sap_settings", current)
    if not ok:
        append_error(db, scope, category="integration", code="SAP_CONNECTION_TEST_FAILED", message=message, entity_type="integration", entity_id="sap_s4hana", retryable=True, details={"baseUrl": base_url})
    append_audit(db, scope, current_user, "INTEGRATION_TESTED", "integration", "sap_s4hana", status="success" if ok else "failed", new_value={"status": current["status"], "message": message})
    return {"status": "success" if ok else "failed", "latencyMs": latency, "checkedAt": now_iso(), "systemVersion": system_version, "message": message, "simulated": bool(system_version == "development-simulation")}


def all_providers(db: Session, scope: str) -> list[dict]:
    providers = deepcopy(PROVIDERS) + get_state(db, scope, "custom_providers", [])
    details = get_state(db, scope, "integration_details", {})
    sap = get_state(db, scope, "sap_settings", deepcopy(SAP_SETTINGS))
    for item in providers:
        if item.get("code") == "sap_s4hana":
            item["status"] = "connected" if sap.get("status") == "connected" else "available"
            item["environment"] = sap.get("environment")
            item["lastTestedAt"] = sap.get("lastTestedAt")
        elif item.get("code") in details:
            saved_provider = (details[item["code"]] or {}).get("provider") or {}
            item.update({key: saved_provider.get(key, item.get(key)) for key in ("status", "environment", "lastTestedAt", "lastSyncAt")})
    return providers


@router.get("/integrations/providers", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def providers(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return all_providers(db, scope_for_user(current_user))


@router.get("/integrations/providers/{code}", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def provider(code: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return require_item(all_providers(db, scope_for_user(current_user)), code, "code")


@router.get("/integrations/{code}", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def integration(code: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    if code == "sap_s4hana":
        detail = provider_detail(require_item(all_providers(db, scope), code, "code"))
        sap = get_state(db, scope, "sap_settings", deepcopy(SAP_SETTINGS))
        detail["settings"].update({"baseUrl": sap.get("baseUrl", ""), "companyCode": sap.get("companyCode", ""), "environment": sap.get("environment", "sandbox"), "enabled": sap.get("status") == "connected"})
        return detail
    details = get_state(db, scope, "integration_details", {})
    return details.get(code) or provider_detail(require_item(all_providers(db, scope), code, "code"))


@router.post("/integrations/custom", status_code=201, dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def custom(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    code = str(payload.get("code") or "").lower().replace(" ", "_")
    value = {"code": code, "name": payload.get("name"), "logoText": (payload.get("name") or "API")[:3].upper(), "type": payload.get("type", "api"), "supportsOAuth": payload.get("authType") == "oauth2", "supportsSandbox": True, "status": "available", "description": payload.get("description", "Custom connector"), "authTypes": [payload.get("authType", "none")], "capabilities": {"connectionTest": True, "fieldMapping": True, "financialMapping": True}}
    values = get_state(db, scope, "custom_providers", [])
    values.append(value)
    set_state(db, scope, "custom_providers", values)
    detail = provider_detail(value)
    detail["settings"].update({"baseUrl": payload.get("baseUrl", ""), "environment": payload.get("environment", "sandbox")})
    _save_detail(db, scope, code, detail)
    append_audit(db, scope, current_user, "INTEGRATION_REGISTERED", "integration", code, new_value=value)
    return detail


@router.put("/integrations/{code}/settings", dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def save_integration_settings(code: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    detail = integration(code, current_user, db)
    _save_secrets(db, scope, code, payload)
    detail["settings"] = {**detail.get("settings", {}), **_safe_settings(payload)}
    return _save_detail(db, scope, code, detail)


@router.put("/integrations/{code}", dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def save_integration(code: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    value = _save_detail(db, scope_for_user(current_user), code, payload)
    append_audit(db, scope_for_user(current_user), current_user, "INTEGRATION_UPDATED", "integration", code, new_value={"enabled": (payload.get("settings") or {}).get("enabled")})
    return value


def _save_detail(db: Session, scope: str, code: str, detail: dict):
    details = get_state(db, scope, "integration_details", {})
    details[code] = detail
    set_state(db, scope, "integration_details", details)
    return detail


@router.post("/integrations/{code}/test", dependencies=[Depends(require_frontend_permission("integrations:test"))])
def test_integration(code: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    if code == "sap_s4hana":
        return test_sap({}, current_user, db)
    scope = scope_for_user(current_user)
    detail = integration(code, current_user, db)
    connector_settings = detail.get("settings") or {}
    checked_at = now_iso()
    if code == "tallyprime":
        ok, latency, message, version = True, 0, "TallyPrime export generation is available locally.", "local-export"
    else:
        secrets_value = get_state(db, scope, "integration_secrets", {}).get(code, {})
        ok, latency, message, version = _probe_connection(str(connector_settings.get("baseUrl") or ""), str(connector_settings.get("authType") or ""), secrets_value)
    result = {"providerCode": code, "status": "success" if ok else "failed", "latencyMs": latency, "checkedAt": checked_at, "message": message, "systemVersion": version, "simulated": bool(version == "development-simulation")}
    detail["provider"]["status"] = "connected" if ok else "available"
    detail["provider"]["environment"] = connector_settings.get("environment")
    detail["provider"]["lastTestedAt"] = checked_at
    _save_detail(db, scope, code, detail)
    if not ok:
        append_error(db, scope, category="integration", code="INTEGRATION_TEST_FAILED", message=message, entity_type="integration", entity_id=code, retryable=True, details={"baseUrl": connector_settings.get("baseUrl")})
    append_audit(db, scope, current_user, "INTEGRATION_TESTED", "integration", code, status="success" if ok else "failed", new_value=result)
    return result


@router.post("/integrations/{code}/sync-master-data", dependencies=[Depends(require_frontend_permission("integrations:sync"))])
def sync_master(code: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    detail = integration(code, current_user, db)
    counts = {"vendors": 0, "customers": 0, "accounts": 0, "taxCodes": 0, "lastSyncedAt": now_iso()}
    detail["masterData"] = counts
    detail["provider"]["lastSyncAt"] = counts["lastSyncedAt"]
    _save_detail(db, scope, code, detail)
    append_audit(db, scope, current_user, "MASTER_DATA_SYNCED", "integration", code, new_value=counts)
    return {"providerCode": code, "status": "completed", "syncedAt": now_iso(), "counts": counts, "message": "No third-party data was imported because external credentials are not configured."}


def _tally_bytes(entries: list[dict], fmt: str) -> tuple[bytes, str]:
    if fmt == "json":
        return json.dumps({"entries": entries}, indent=2, default=str).encode("utf-8"), "application/json"
    if fmt == "csv":
        stream = io.StringIO()
        writer = csv.writer(stream)
        writer.writerow(["entry_id", "date", "description", "amount", "currency", "category", "gl_account"])
        for entry in entries:
            writer.writerow([entry.get("entryId"), entry.get("date"), entry.get("englishDescription"), entry.get("amount"), entry.get("currency"), entry.get("category"), entry.get("glAccount")])
        return stream.getvalue().encode("utf-8"), "text/csv"
    vouchers = []
    for entry in entries:
        vouchers.append(f"<VOUCHER><REFERENCE>{escape(str(entry.get('entryId') or ''))}</REFERENCE><DATE>{escape(str(entry.get('date') or ''))}</DATE><NARRATION>{escape(str(entry.get('englishDescription') or ''))}</NARRATION><AMOUNT>{entry.get('amount') or 0}</AMOUNT><CURRENCY>{escape(str(entry.get('currency') or ''))}</CURRENCY><CATEGORY>{escape(str(entry.get('category') or ''))}</CATEGORY></VOUCHER>")
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?><ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA><REQUESTDATA>" + "".join(vouchers) + "</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>"
    return xml.encode("utf-8"), "application/xml"


@router.get("/integrations/tallyprime/exports", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def tally_exports(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [{key: value for key, value in item.items() if not key.startswith("_")} for item in get_state(db, scope_for_user(current_user), "tally_exports", [])]


@router.post("/integrations/tallyprime/exports", status_code=201, dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def create_tally(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    entries = ensure_entries(db, scope)
    fmt = str(payload.get("format") or "xml").lower()
    if fmt not in {"xml", "json", "csv"}:
        raise HTTPException(status_code=422, detail="Tally export format must be XML, JSON, or CSV.")
    export_id = new_id("tally")
    filename = safe_filename(f"tally-export-{datetime.now(timezone.utc):%Y%m%d%H%M%S}.{fmt}")
    EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
    path = EXPORT_ROOT / f"{export_id}_{filename}"
    content, media_type = _tally_bytes(entries, fmt)
    path.write_bytes(content)
    job = {**payload, "id": export_id, "companyName": "Current company", "status": "completed", "recordsExported": len(entries), "retryable": False, "createdAt": now_iso(), "createdBy": getattr(current_user, "full_name", None) or getattr(current_user, "email", "User"), "completedAt": now_iso(), "fileName": filename, "requestId": new_id("req"), "_filePath": str(path), "_mediaType": media_type}
    values = get_state(db, scope, "tally_exports", [])
    values.insert(0, job)
    set_state(db, scope, "tally_exports", values)
    tally_detail = integration("tallyprime", current_user, db)
    tally_detail["settings"]["enabled"] = True
    tally_detail["provider"]["status"] = "connected"
    tally_detail["provider"]["lastSyncAt"] = now_iso()
    _save_detail(db, scope, "tallyprime", tally_detail)
    append_audit(db, scope, current_user, "TALLY_EXPORT_CREATED", "integration", export_id, new_value={"fileName": filename, "recordsExported": len(entries)})
    return {key: value for key, value in job.items() if not key.startswith("_")}


@router.post("/integrations/tallyprime/exports/{export_id}/retry", dependencies=[Depends(require_frontend_permission("integrations:manage"))])
def retry_tally(export_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    values = get_state(db, scope, "tally_exports", [])
    item = require_item(values, export_id)
    content, media_type = _tally_bytes(ensure_entries(db, scope), item.get("format", "xml"))
    raw_path = str(item.get("_filePath") or "").strip()
    if raw_path:
        path = Path(raw_path)
    else:
        EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
        path = EXPORT_ROOT / f"{export_id}_{safe_filename(item.get('fileName') or 'tally-export.xml')}"
    path.write_bytes(content)
    item.update({"status": "completed", "retryable": False, "completedAt": now_iso(), "errorMessage": None, "_filePath": str(path), "_mediaType": media_type})
    set_state(db, scope, "tally_exports", values)
    append_audit(db, scope, current_user, "TALLY_EXPORT_RETRIED", "integration", export_id, new_value={"status": "completed"})
    return {key: value for key, value in item.items() if not key.startswith("_")}


@router.get("/integrations/tallyprime/exports/{export_id}/download", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def tally_download(export_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = require_item(get_state(db, scope_for_user(current_user), "tally_exports", []), export_id)
    return {"exportId": export_id, "fileName": item.get("fileName"), "downloadUrl": f"/integrations/tallyprime/exports/{export_id}/content", "expiresAt": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}


@router.get("/integrations/tallyprime/exports/{export_id}/content", dependencies=[Depends(require_frontend_permission("integrations:read"))])
def tally_content(export_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    item = require_item(get_state(db, scope, "tally_exports", []), export_id)
    path = Path(str(item.get("_filePath") or ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="The generated Tally export file is no longer available. Retry the export to regenerate it.")
    append_audit(db, scope, current_user, "TALLY_EXPORT_DOWNLOADED", "integration", export_id, new_value={"fileName": item.get("fileName")})
    return FileResponse(path, media_type=item.get("_mediaType") or "application/octet-stream", filename=item.get("fileName") or path.name)
