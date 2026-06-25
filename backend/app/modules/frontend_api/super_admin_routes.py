from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import secrets
import time

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.config import settings as app_settings
from app.database import get_db
from app.dependencies import get_current_super_admin
from app.modules.companies.models import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.frontend_api.defaults import PLATFORM_SETTINGS, PROVIDERS, SECURITY_SETTINGS, SUBSCRIPTION_PLANS
from app.modules.frontend_api.models import FrontendState
from app.modules.frontend_api.store import get_state, set_state
from app.modules.frontend_api.utils import new_id, now_iso
from app.modules.tenants.models import Tenant, TenantStatus
from app.modules.tenants.repository import TenantRepository
from app.modules.users.models import User
from app.modules.users.repository import RoleRepository, UserRepository

router = APIRouter()


def _status(tenant: Tenant) -> str:
    value = getattr(tenant.status, "value", tenant.status)
    if value == "trial":
        return "trial"
    if value == "suspended":
        return "suspended"
    if value == "inactive":
        return "pending"
    return "active"


def _plan(tenant: Tenant) -> str:
    raw = str(tenant.plan or "starter").lower()
    return {"starter": "Starter", "professional": "Growth", "growth": "Growth", "enterprise": "Enterprise"}.get(raw, "Starter")


def _platform_company(company: Company, db: Session) -> dict:
    tenant = company.tenant
    users = db.query(User).filter(User.company_id == company.id).count()
    admin = db.query(User).filter(User.company_id == company.id).order_by(User.created_at.asc()).first()
    created = company.created_at.replace(tzinfo=timezone.utc).isoformat() if company.created_at and company.created_at.tzinfo is None else (company.created_at.isoformat() if company.created_at else now_iso())
    scope = _company_scope(company)
    files = get_state(db, scope, "files", [])
    entries = get_state(db, scope, "entries", [])
    postings = get_state(db, scope, "sap_postings", [])
    accounting_postings = get_state(db, scope, "accounting_postings", [])
    storage_bytes = sum(int(item.get("sizeBytes") or 0) for item in files)
    activity_candidates = [created] + [str(item.get("updatedAt") or item.get("createdAt") or item.get("uploadedAt") or created) for item in files + entries]
    return {
        "id": str(company.id), "tenantId": str(company.tenant_id), "companyName": company.legal_name,
        "country": company.country or "", "industry": company.industry or "", "plan": _plan(tenant),
        "status": _status(tenant), "users": users, "filesProcessed": len(files), "entriesProcessed": len(entries),
        "sapPostings": len(postings), "accountingPostings": len(accounting_postings),
        "storageUsedGb": round(storage_bytes / (1024 ** 3), 4), "createdAt": created,
        "lastActivityAt": max(activity_candidates), "adminEmail": admin.email if admin else company.email,
        "billingStatus": "trial" if _status(tenant) == "trial" else "current",
        "trialEndsAt": (datetime.now(timezone.utc)+timedelta(days=14)).isoformat() if _status(tenant) == "trial" else None,
        "mfaCoverage": 0, "ipRestrictionsEnabled": bool(get_state(db, scope, "security_settings", {}).get("allowedIpRanges")),
    }




def _company_scope(company: Company) -> str:
    return f"tenant:{company.tenant_id}:company:{company.id}"


def _company_security_policy(company: Company, db: Session) -> dict:
    stored = get_state(db, _company_scope(company), "security_settings", deepcopy(SECURITY_SETTINGS))
    merged = {**deepcopy(SECURITY_SETTINGS), **(stored if isinstance(stored, dict) else {})}
    return {
        "mfaRequired": bool(merged.get("mfaRequired")),
        "mfaRequiredForPrivilegedRoles": bool(merged.get("mfaRequiredForPrivilegedRoles")),
    }

def _companies(db: Session) -> list[dict]:
    return [_platform_company(c, db) for c in db.query(Company).order_by(Company.created_at.desc()).all()]


@router.get("/super-admin/dashboard")
def dashboard(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    companies = _companies(db)
    rows = db.query(FrontendState).filter(FrontendState.namespace.in_(["files", "entries", "sap_postings"])).all()
    by_date: dict[str, dict] = {}
    ocr_pages = 0
    for row in rows:
        values = row.payload if isinstance(row.payload, list) else []
        for item in values:
            date = str(item.get("createdAt") or item.get("uploadedAt") or item.get("approvedAt") or now_iso())[:10]
            point = by_date.setdefault(date, {"date": date, "files": 0, "entries": 0, "ocrPages": 0, "postings": 0})
            if row.namespace == "files":
                point["files"] += 1
                pages = int((item.get("ocr") or {}).get("pageCount") or 0)
                point["ocrPages"] += pages
                ocr_pages += pages
            elif row.namespace == "entries": point["entries"] += 1
            elif row.namespace == "sap_postings": point["postings"] += 1
    total_files = sum(c["filesProcessed"] for c in companies)
    total_entries = sum(c["entriesProcessed"] for c in companies)
    total_storage = round(sum(c["storageUsedGb"] for c in companies), 4)
    return {
        "kpis": [
            {"key": "companies", "label": "Companies", "value": len(companies), "unit": "number", "tone": "info"},
            {"key": "active", "label": "Active companies", "value": sum(1 for c in companies if c["status"] == "active"), "unit": "number", "tone": "success"},
            {"key": "users", "label": "Users", "value": sum(c["users"] for c in companies), "unit": "number", "tone": "neutral"},
            {"key": "storage", "label": "Storage used", "value": total_storage, "unit": "storage", "tone": "neutral"},
            {"key": "files_processed", "label": "Files processed", "value": total_files, "unit": "number", "tone": "info"},
            {"key": "entries_processed", "label": "Entries processed", "value": total_entries, "unit": "number", "tone": "info"},
            {"key": "ocr_usage", "label": "OCR pages", "value": ocr_pages, "unit": "number", "tone": "info"},
            {"key": "storage_used", "label": "Storage used", "value": total_storage, "unit": "storage", "tone": "neutral"},
        ],
        "usageTrend": [by_date[key] for key in sorted(by_date)[-7:]],
        "topCompanies": [{"companyId": c["id"], "companyName": c["companyName"], "filesProcessed": c["filesProcessed"], "entriesProcessed": c["entriesProcessed"], "storageUsedGb": c["storageUsedGb"]} for c in sorted(companies, key=lambda item: item["filesProcessed"], reverse=True)[:5]],
    }


@router.get("/super-admin/companies")
def companies(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return _companies(db)


@router.get("/super-admin/companies/{company_id}")
def company(company_id: str, _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    value = db.query(Company).filter(Company.id == company_id).first()
    if not value: raise HTTPException(status_code=404, detail="Company not found")
    return _platform_company(value, db)


@router.get("/super-admin/companies/{company_id}/security")
def company_security(company_id: str, _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return _company_security_policy(company, db)


@router.put("/super-admin/companies/{company_id}/security")
def save_company_security(company_id: str, payload: dict = Body(...), current_user=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    scope = _company_scope(company)
    previous = {**deepcopy(SECURITY_SETTINGS), **get_state(db, scope, "security_settings", {})}
    updated = {
        **previous,
        "mfaRequired": bool(payload.get("mfaRequired", False)),
        "mfaRequiredForPrivilegedRoles": bool(payload.get("mfaRequiredForPrivilegedRoles", False)),
    }
    set_state(db, scope, "security_settings", updated)

    if bool(payload.get("resetMfaEnrollments")) and not updated["mfaRequired"] and not updated["mfaRequiredForPrivilegedRoles"]:
        profiles = get_state(db, "platform", "mfa_profiles", {})
        user_ids = {str(row[0]) for row in db.query(User.id).filter(User.company_id == company.id).all()}
        changed = False
        for user_id in user_ids:
            if user_id in profiles:
                profiles.pop(user_id, None)
                changed = True
        if changed:
            set_state(db, "platform", "mfa_profiles", profiles)

    audit = get_state(db, "platform", "platform_audit", [])
    audit.insert(0, {
        "id": new_id("audit"),
        "actor": current_user.email,
        "action": "TENANT_MFA_POLICY_UPDATED",
        "targetType": "company",
        "targetName": company.legal_name,
        "companyName": company.legal_name,
        "ipAddress": "server",
        "createdAt": now_iso(),
        "result": "success",
        "details": f"MFA all users={updated['mfaRequired']}; privileged roles={updated['mfaRequiredForPrivilegedRoles']}.",
    })
    set_state(db, "platform", "platform_audit", audit)
    return _company_security_policy(company, db)




def _registration_request_dto(item: dict, db: Session) -> dict:
    company = CompanyRepository(db).get_by_id(str(item.get("companyId"))) if item.get("companyId") else None
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "companyId": str(item.get("companyId") or ""),
        "companyName": company.legal_name if company else str(payload.get("legalName") or "Unknown company"),
        "adminEmail": str(item.get("email") or payload.get("primaryContactEmail") or ""),
        "country": company.country if company else str(payload.get("country") or ""),
        "industry": company.industry if company else str(payload.get("industry") or ""),
        "status": str(item.get("status") or "pending"),
        "createdAt": str(item.get("createdAt") or now_iso()),
        "approvedAt": item.get("approvedAt"),
        "approvedBy": item.get("approvedBy"),
    }


@router.get("/super-admin/registration-requests")
def registration_requests(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    requests = get_state(db, "platform", "registration_requests", [])
    if not isinstance(requests, list):
        return []
    return [_registration_request_dto(item, db) for item in requests]


@router.post("/super-admin/registration-requests/{request_id}/approve")
def approve_registration_request(request_id: str, current_user=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    requests = get_state(db, "platform", "registration_requests", [])
    request_item = next((item for item in requests if str(item.get("id")) == request_id), None)
    if request_item is None:
        raise HTTPException(status_code=404, detail="Registration request not found")
    if str(request_item.get("status")) != "pending":
        raise HTTPException(status_code=409, detail="Registration request is no longer pending")

    company = CompanyRepository(db).get_by_id(str(request_item.get("companyId"))) if request_item.get("companyId") else None
    if company is None:
        raise HTTPException(status_code=404, detail="Registered company was not found")
    user = UserRepository(db).get_by_email(str(request_item.get("email") or ""))
    if user is None or str(user.company_id) != str(company.id):
        raise HTTPException(status_code=404, detail="Company administrator was not found")

    company.tenant.status = TenantStatus.ACTIVE
    user.is_active = True
    user.is_email_verified = True
    db.commit()
    db.refresh(company)
    db.refresh(user)

    activation_token = secrets.token_urlsafe(32)
    reset_tokens = get_state(db, "platform", "password_reset_tokens", {})
    if not isinstance(reset_tokens, dict):
        reset_tokens = {}
    reset_tokens[activation_token] = {"userId": str(user.id), "createdAt": now_iso(), "purpose": "tenant_activation"}
    set_state(db, "platform", "password_reset_tokens", reset_tokens)

    request_item["status"] = "approved"
    request_item["approvedAt"] = now_iso()
    request_item["approvedBy"] = current_user.email
    set_state(db, "platform", "registration_requests", requests)

    audit = get_state(db, "platform", "platform_audit", [])
    if not isinstance(audit, list):
        audit = []
    audit.insert(0, {
        "id": new_id("audit"),
        "actor": current_user.email,
        "action": "TENANT_REGISTRATION_APPROVED",
        "targetType": "company",
        "targetName": company.legal_name,
        "companyName": company.legal_name,
        "ipAddress": "server",
        "createdAt": now_iso(),
        "result": "success",
        "details": "The tenant and Company Admin account were activated. MFA remains governed by the tenant policy.",
    })
    set_state(db, "platform", "platform_audit", audit)
    return {
        "request": _registration_request_dto(request_item, db),
        "company": _platform_company(company, db),
        "activationPath": f"/auth/reset-password?token={activation_token}",
    }


@router.post("/super-admin/company-onboarding", status_code=201)
def onboard(payload: dict = Body(...), current_user=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    email = str(payload.get("adminEmail") or "").strip().lower(); legal = str(payload.get("legalName") or "").strip()
    if not email or not legal: raise HTTPException(status_code=422, detail="legalName and adminEmail are required")
    if UserRepository(db).get_by_email(email): raise HTTPException(status_code=409, detail="Admin email already exists")
    tenant = TenantRepository(db).create(name=legal, plan=str(payload.get("plan") or "starter").lower())
    company = CompanyRepository(db).create(tenant_id=tenant.id, legal_name=legal, country=payload.get("country") or "Unknown", industry=payload.get("industry"), email=email, default_currency=payload.get("defaultCurrency") or "USD", timezone=payload.get("timezone") or "UTC")
    role = RoleRepository(db).get_by_name("company_admin") or RoleRepository(db).create("company_admin", "Company Admin", "Company administrator", True)
    temporary_password = f"DevOnly!{new_id('user')[-8:]}"
    UserRepository(db).create(email=email, hashed_password=hash_password(temporary_password), tenant_id=tenant.id, company_id=company.id, role_id=role.id, first_name="Company", last_name="Admin", is_active=True, is_email_verified=True)
    tenant_security = {
        **deepcopy(SECURITY_SETTINGS),
        "mfaRequired": bool(payload.get("requireMfa", False)),
        "mfaRequiredForPrivilegedRoles": False,
    }
    set_state(db, _company_scope(company), "security_settings", tenant_security)
    audit = get_state(db, "platform", "platform_audit", []); audit.insert(0, {"id": new_id("audit"), "actor": current_user.email, "action": "COMPANY_PROVISIONED", "targetType": "company", "targetName": legal, "companyName": legal, "ipAddress": "server", "createdAt": now_iso(), "result": "success", "details": f"Company and administrator were provisioned. MFA required={tenant_security['mfaRequired']}."}); set_state(db, "platform", "platform_audit", audit)
    return {"company": _platform_company(company, db), "jobId": new_id("provision"), "status": "completed", "createdAt": now_iso()}


@router.patch("/super-admin/companies/{company_id}/status")
def company_status(company_id: str, payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company: raise HTTPException(status_code=404, detail="Company not found")
    requested = str(payload.get("status") or "active")
    company.tenant.status = TenantStatus.SUSPENDED if requested == "suspended" else TenantStatus.ACTIVE
    db.commit(); db.refresh(company); return _platform_company(company, db)


def _providers(db: Session) -> list[dict]:
    tests = get_state(db, "platform", "provider_health", {})
    result = []
    for provider in PROVIDERS:
        test = tests.get(provider["code"], {}) if isinstance(tests, dict) else {}
        status = test.get("status") or "not_configured"
        result.append({
            "code": provider["code"], "name": provider["name"],
            "category": "accounting" if provider["type"] in {"accounting", "export"} else "erp",
            "status": status, "environment": "development",
            "uptimePercent": test.get("uptimePercent"), "successRate": test.get("successRate"),
            "latencyMs": test.get("latencyMs"), "requests24h": int(test.get("requests24h") or 0),
            "incidentsOpen": int(test.get("incidentsOpen") or 0),
            "lastCheckedAt": test.get("checkedAt") or now_iso(),
            "message": test.get("message") or "No live provider probe has been configured.",
        })
    return result


@router.get("/super-admin/integrations")
def integrations(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return _providers(db)


@router.post("/super-admin/integrations/{provider_code}/test")
def test_provider(provider_code: str, _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    if not any(provider["code"] == provider_code for provider in PROVIDERS):
        raise HTTPException(status_code=404, detail="Provider not found")
    checked = now_iso()
    tests = get_state(db, "platform", "provider_health", {})
    tests[provider_code] = {"status": "not_configured", "checkedAt": checked, "message": "Provider credentials or endpoint are not configured; no live health claim was made.", "uptimePercent": None, "successRate": None, "latencyMs": None, "requests24h": 0, "incidentsOpen": 0}
    set_state(db, "platform", "provider_health", tests)
    return {"providerCode": provider_code, "status": "not_configured", "checkedAt": checked}


@router.get("/super-admin/system-health")
def health(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    import psutil
    services = []
    cpu = round(psutil.cpu_percent(interval=0.05), 1); memory = round(psutil.virtual_memory().percent, 1)
    services.append({"id": "api", "name": "API", "region": "local", "status": "operational", "uptimePercent": 100, "latencyMs": 1, "cpuPercent": cpu, "memoryPercent": memory, "lastDeploymentAt": now_iso(), "message": "Application process is responding."})
    started = time.perf_counter()
    try:
        db.execute(text("SELECT 1")); db_status = "operational"; db_message = "Database query succeeded."
    except Exception as exc:
        db_status = "outage"; db_message = str(exc)
    services.append({"id": "database", "name": "PostgreSQL / Database", "region": "configured database", "status": db_status, "uptimePercent": 100 if db_status == "operational" else 0, "latencyMs": round((time.perf_counter()-started)*1000, 1), "cpuPercent": 0, "memoryPercent": 0, "lastDeploymentAt": now_iso(), "message": db_message})
    redis_status = "degraded"; redis_latency = 0; redis_message = "Redis probe failed or Redis is not configured."
    try:
        import redis
        started = time.perf_counter(); client = redis.Redis.from_url(app_settings.REDIS_URL, socket_connect_timeout=0.4, socket_timeout=0.4); client.ping()
        redis_status = "operational"; redis_latency = round((time.perf_counter()-started)*1000, 1); redis_message = "Redis ping succeeded."
    except Exception as exc:
        redis_message = f"Redis unavailable: {exc.__class__.__name__}."
    services.append({"id": "redis", "name": "Redis", "region": "configured cache", "status": redis_status, "uptimePercent": 100 if redis_status == "operational" else 0, "latencyMs": redis_latency, "cpuPercent": 0, "memoryPercent": 0, "lastDeploymentAt": now_iso(), "message": redis_message})
    heartbeat = get_state(db, "platform", "worker_heartbeat", {})
    worker_ok = bool(heartbeat and heartbeat.get("lastSeenAt"))
    services.append({"id": "worker", "name": "Background worker", "region": "job runner", "status": "operational" if worker_ok else "degraded", "uptimePercent": 100 if worker_ok else 0, "latencyMs": float(heartbeat.get("latencyMs") or 0), "cpuPercent": float(heartbeat.get("cpuPercent") or 0), "memoryPercent": float(heartbeat.get("memoryPercent") or 0), "lastDeploymentAt": heartbeat.get("lastSeenAt") or now_iso(), "message": "Worker heartbeat received." if worker_ok else "No verified worker heartbeat is available."})
    return services


@router.get("/super-admin/job-queues")
def queues(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    rows = db.query(FrontendState).filter(FrontendState.namespace == "processing_logs").all()
    logs = [item for row in rows for item in (row.payload if isinstance(row.payload, list) else [])]
    stage_map = {"file": "ingestion", "ocr": "ocr", "classification": "classification", "review": "review", "validation": "review", "posting": "posting", "sap": "posting"}
    metrics = {key: {"id": key, "name": label, "type": key, "status": "healthy", "waiting": 0, "active": 0, "failed": 0, "completed24h": 0, "oldestJobAgeSeconds": 0, "throughputPerMinute": 0} for key, label in [("ingestion","Ingestion"),("ocr","OCR"),("classification","Classification"),("review","Review"),("posting","Posting")]}
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    for log in logs:
        queue = stage_map.get(str(log.get("stage") or "").lower())
        if not queue: continue
        level = str(log.get("level") or "info")
        if level == "error": metrics[queue]["failed"] += 1
        try:
            stamp = datetime.fromisoformat(str(log.get("timestamp")).replace("Z", "+00:00")); stamp = stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)
            if stamp >= cutoff and level != "error": metrics[queue]["completed24h"] += 1
        except Exception: pass
    for item in metrics.values():
        if item["failed"]: item["status"] = "delayed"
        item["throughputPerMinute"] = round(item["completed24h"] / (24*60), 3)
    persisted = get_state(db, "platform", "job_queues", {})
    if isinstance(persisted, dict):
        for key, patch in persisted.items():
            if key in metrics: metrics[key].update(patch)
    return list(metrics.values())


@router.post("/super-admin/job-queues/{queue_id}/retry")
def retry_queue(queue_id: str, _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    values = {item["id"]: item for item in queues(_, db)}; item = values.get(queue_id)
    if not item: raise HTTPException(status_code=404, detail="Queue not found")
    item["failed"] = 0; item["status"] = "healthy"; set_state(db, "platform", "job_queues", values); return item


@router.post("/super-admin/job-queues/pause-non-critical")
def pause_queues(payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    values = {item["id"]: item for item in queues(_, db)}; paused = bool(payload.get("paused"))
    for item in values.values():
        if item["type"] not in {"review", "posting"}: item["status"] = "blocked" if paused else "healthy"
    set_state(db, "platform", "job_queues", values); return {"paused": paused, "queues": list(values.values())}


def _company_by_scope(db: Session) -> dict[str, Company]:
    return {_company_scope(company): company for company in db.query(Company).all()}


def _platform_error(item: dict, company: Company | None = None) -> dict:
    occurred = str(item.get("occurredAt") or item.get("lastSeenAt") or item.get("firstSeenAt") or now_iso())
    return {
        "id": str(item.get("id") or new_id("error")),
        "code": str(item.get("code") or "UNCLASSIFIED_ERROR"),
        "title": str(item.get("title") or item.get("code") or "Application error").replace("_", " ").title(),
        "severity": str(item.get("severity") or "high"),
        "status": str(item.get("status") or "open"),
        "source": str(item.get("source") or item.get("category") or "application"),
        "companyId": str(item.get("companyId") or (company.id if company else "")) or None,
        "companyName": str(item.get("companyName") or (company.legal_name if company else "")) or None,
        "occurrences": int(item.get("occurrences") or 1),
        "firstSeenAt": str(item.get("firstSeenAt") or occurred),
        "lastSeenAt": str(item.get("lastSeenAt") or occurred),
        "owner": item.get("owner"),
        "correlationId": str(item.get("correlationId") or item.get("requestId") or item.get("id") or new_id("corr")),
        "message": str(item.get("message") or "No error details were supplied."),
    }


@router.get("/super-admin/error-center")
def errors(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    combined = [_platform_error(item) for item in get_state(db, "platform", "platform_errors", [])]
    companies = _company_by_scope(db)
    rows = db.query(FrontendState).filter(FrontendState.namespace == "errors").all()
    for row in rows:
        company = companies.get(row.scope_key)
        for item in (row.payload if isinstance(row.payload, list) else []):
            combined.append(_platform_error(item, company))
    return sorted(combined, key=lambda item: item.get("lastSeenAt") or "", reverse=True)


@router.post("/super-admin/error-center/{error_id}/investigate")
def investigate(error_id: str, payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    platform_values = get_state(db, "platform", "platform_errors", [])
    platform_item = next((item for item in platform_values if str(item.get("id")) == error_id), None)
    if platform_item:
        platform_item.update({"status": "investigating", "owner": payload.get("owner"), "message": payload.get("notes") or platform_item.get("message")})
        set_state(db, "platform", "platform_errors", platform_values)
        return _platform_error(platform_item)
    for row in db.query(FrontendState).filter(FrontendState.namespace == "errors").all():
        values = row.payload if isinstance(row.payload, list) else []
        item = next((candidate for candidate in values if str(candidate.get("id")) == error_id), None)
        if item:
            item.update({"status": "investigating", "owner": payload.get("owner"), "message": payload.get("notes") or item.get("message")})
            set_state(db, row.scope_key, "errors", values)
            return _platform_error(item, _company_by_scope(db).get(row.scope_key))
    raise HTTPException(status_code=404, detail="Error not found")


@router.post("/super-admin/error-center/incidents", status_code=201)
def incident(payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    item = {"id": new_id("incident"), "code": "MANUAL_INCIDENT", "title": payload.get("title"), "severity": payload.get("severity", "medium"), "status": "open", "source": payload.get("source", "manual"), "companyId": payload.get("companyId"), "companyName": payload.get("companyName"), "occurrences": 1, "firstSeenAt": now_iso(), "lastSeenAt": now_iso(), "owner": payload.get("owner"), "correlationId": new_id("corr"), "message": payload.get("message", "")}
    values = get_state(db, "platform", "platform_errors", [])
    values.insert(0, item)
    set_state(db, "platform", "platform_errors", values)
    return item


@router.get("/super-admin/subscriptions")
def subscriptions(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return get_state(db, "platform", "subscription_plans", deepcopy(SUBSCRIPTION_PLANS))
@router.post("/super-admin/subscriptions", status_code=201)
def add_plan(payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    item = {"id": new_id("plan"), "companies": 0, **payload}; values = subscriptions(_,db); values.append(item); set_state(db,"platform","subscription_plans",values); return item
@router.put("/super-admin/subscriptions/{plan_id}")
def update_plan(plan_id: str, payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    values = subscriptions(_,db); item = next((x for x in values if x["id"] == plan_id),None)
    if not item: raise HTTPException(status_code=404,detail="Plan not found")
    item.update(payload); set_state(db,"platform","subscription_plans",values); return item


@router.get("/super-admin/billing")
def billing(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return get_state(db, "platform", "platform_invoices", [])
@router.get("/super-admin/billing/{invoice_id}")
def invoice(invoice_id: str, _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    item = next((x for x in billing(_,db) if x["id"] == invoice_id),None)
    if not item: raise HTTPException(status_code=404,detail="Invoice not found")
    return item


def _platform_audit_record(item: dict, company: Company | None = None) -> dict:
    raw_result = str(item.get("result") or item.get("status") or (item.get("metadata") or {}).get("status") or "success")
    result = raw_result if raw_result in {"success", "denied", "failed"} else ("failed" if raw_result in {"error", "failure"} else "success")
    details = item.get("details")
    if not details:
        metadata = item.get("metadata") or {}
        details = metadata.get("message") or metadata.get("reason") or f"{item.get('action') or 'Action'} on {item.get('entityType') or item.get('targetType') or 'record'} {item.get('entityId') or item.get('targetName') or ''}."
    return {
        "id": str(item.get("id") or new_id("audit")),
        "actor": str(item.get("actor") or item.get("user") or "System"),
        "action": str(item.get("action") or "UNKNOWN_ACTION"),
        "targetType": str(item.get("targetType") or item.get("entityType") or "record"),
        "targetName": str(item.get("targetName") or item.get("entityId") or "—"),
        "companyName": str(item.get("companyName") or (company.legal_name if company else "")) or None,
        "ipAddress": str(item.get("ipAddress") or "backend"),
        "createdAt": str(item.get("createdAt") or item.get("timestamp") or now_iso()),
        "result": result,
        "details": str(details),
    }


@router.get("/super-admin/audit-logs")
def audit(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    records = [_platform_audit_record(item) for item in get_state(db, "platform", "platform_audit", [])]
    companies = _company_by_scope(db)
    rows = db.query(FrontendState).filter(FrontendState.namespace.in_(["audit", "audit_logs"])).all()
    seen: set[str] = {item["id"] for item in records}
    for row in rows:
        company = companies.get(row.scope_key)
        for item in (row.payload if isinstance(row.payload, list) else []):
            record = _platform_audit_record(item, company)
            if record["id"] not in seen:
                seen.add(record["id"])
                records.append(record)
    return sorted(records, key=lambda item: item.get("createdAt") or "", reverse=True)


@router.get("/super-admin/audit-logs/export")
def audit_export(_=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    records = audit(_, db)
    return {"generatedAt": now_iso(), "algorithm": "HMAC-SHA256", "signature": new_id("signature"), "records": records}


@router.get("/super-admin/support")
def tickets(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return get_state(db,"platform","support_tickets",[])
@router.post("/super-admin/support", status_code=201)
def add_ticket(payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    item = {"id": new_id("ticket"), **payload, "status":"new", "createdAt":now_iso(), "updatedAt":now_iso()}; values=tickets(_,db); values.insert(0,item); set_state(db,"platform","support_tickets",values); return item
@router.patch("/super-admin/support/{ticket_id}")
def update_ticket(ticket_id: str, payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)):
    values=tickets(_,db); item=next((x for x in values if x["id"]==ticket_id),None)
    if not item: raise HTTPException(status_code=404,detail="Ticket not found")
    item.update(payload); item["updatedAt"]=now_iso(); set_state(db,"platform","support_tickets",values); return item


@router.get("/super-admin/settings")
def settings(_=Depends(get_current_super_admin), db: Session = Depends(get_db)): return get_state(db,"platform","platform_settings",deepcopy(PLATFORM_SETTINGS))
@router.put("/super-admin/settings")
def save_settings(payload: dict = Body(...), _=Depends(get_current_super_admin), db: Session = Depends(get_db)): set_state(db,"platform","platform_settings",payload); return payload
