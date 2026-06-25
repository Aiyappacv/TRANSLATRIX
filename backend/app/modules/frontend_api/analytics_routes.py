from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.frontend_api.defaults import role_dashboard
from app.modules.frontend_api.finance_routes import ensure_entries, ensure_review
from app.modules.frontend_api.integration_routes import ensure_postings
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import require_item
from app.modules.ingestion.data_intake_models import IntakeRegistry, IntakeStatus

router = APIRouter()

READY_OR_EXTRACTED_STATUSES = (
    IntakeStatus.METADATA_READY,
    IntakeStatus.READY_FOR_EXTRACTION,
    IntakeStatus.EXTRACTING,
    IntakeStatus.EXTRACTED,
)


def _intake_registry_counts(db: Session, current_user) -> tuple[int, int]:
    """Live counts straight from the Data Intake registry: (total documents, ready/extracted documents).

    This is the source of truth for "documents ingested" — independent of whether
    anyone has bridged a document into the extraction workspace yet.
    """
    tenant_id = getattr(current_user, "tenant_id", None)
    company_id = getattr(current_user, "company_id", None)
    if not tenant_id or not company_id:
        return 0, 0
    query = db.query(IntakeRegistry).filter(
        IntakeRegistry.tenant_id == tenant_id,
        IntakeRegistry.company_id == company_id,
    )
    total = query.count()
    ready_or_extracted = query.filter(IntakeRegistry.status.in_(READY_OR_EXTRACTED_STATUSES)).count()
    return total, ready_or_extracted


def _percent(value: float) -> str:
    return f"{round(value * 100)}%"


def _date(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).date().isoformat()
    return str(value)[:10]


@router.get("/analytics/summary", dependencies=[Depends(require_frontend_permission("dashboard:read"))])
def dashboard_summary(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = get_state(db, scope, "files", [])
    entries = ensure_entries(db, scope)
    reviews, _ = ensure_review(db, scope)
    postings = ensure_postings(db, scope, current_user) if "posting:read" in getattr(current_user, "_frontend_permissions", []) else get_state(db, scope, "sap_postings", [])
    posted = sum(1 for entry in entries if entry.get("status") == "sap_posted")
    intake_total, intake_ready_or_extracted = _intake_registry_counts(db, current_user)
    grouped: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "entries": 0})
    for file in files:
        grouped[_date(file.get("createdAt"))]["files"] += 1
    for entry in entries:
        grouped[_date(entry.get("createdAt"))]["entries"] += 1
    classification = Counter(entry.get("category") or "Unclassified" for entry in entries)
    return {
        "kpis": [
            {"label": "Files ingested", "value": str(intake_total), "delta": "Live from Data Intake", "tone": "info"},
            {"label": "Documents ready/extracted", "value": str(intake_ready_or_extracted), "delta": "Live from Data Intake", "tone": "info"},
            {"label": "Pending review", "value": str(sum(1 for review in reviews if review.get("status") not in {"approved", "rejected"})), "delta": "Current queue", "tone": "warning"},
            {"label": "SAP posted", "value": str(posted), "delta": "Persisted results", "tone": "success"},
        ],
        "processingTrend": [{"period": period, **values} for period, values in sorted(grouped.items())],
        "classificationSplit": [{"label": label, "value": value} for label, value in classification.items()],
        "postingReady": sum(1 for record in postings if record.get("sapStatus") == "ready"),
    }


@router.get("/dashboards/{role}", dependencies=[Depends(require_frontend_permission("dashboard:read"))])
def role_dashboard_endpoint(role: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    data = role_dashboard(role)
    scope = scope_for_user(current_user)
    files = get_state(db, scope, "files", [])
    entries = ensure_entries(db, scope)
    reviews, _ = ensure_review(db, scope)
    postings = get_state(db, scope, "sap_postings", [])
    errors = get_state(db, scope, "errors", [])
    providers = get_state(db, scope, "integration_connections", [])

    pending_reviews = [item for item in reviews if item.get("status") not in {"approved", "rejected"}]
    ready = sum(1 for item in postings if item.get("sapStatus") == "ready")
    posted = sum(1 for item in postings if item.get("sapStatus") == "posted")
    failed = sum(1 for item in postings if item.get("sapStatus") == "failed")
    retryable = sum(1 for item in errors if item.get("category") == "sap_posting" and item.get("retryable") and item.get("status", "open") != "resolved")
    non_retryable = sum(1 for item in errors if item.get("category") == "sap_posting" and not item.get("retryable") and item.get("status", "open") != "resolved")
    attempted = posted + failed
    success_rate = round(posted / attempted * 100) if attempted else 0
    intake_total, intake_ready_or_extracted = _intake_registry_counts(db, current_user)

    data["kpis"][0]["value"] = str(intake_total)
    data["kpis"][0]["delta"] = "Live from Data Intake"
    data["kpis"][1]["label"] = "Documents ready/extracted"
    data["kpis"][1]["value"] = str(intake_ready_or_extracted)
    data["kpis"][1]["delta"] = "Live from Data Intake"
    data["kpis"][2]["value"] = str(len(pending_reviews))
    data["kpis"][2]["delta"] = "Current queue; no seeded fallback"
    data["kpis"][3]["value"] = str(posted)
    if role == "sap_poster":
        data["kpis"] = [
            {"key": "ready", "label": "Ready to post", "value": str(ready), "delta": "Approved and eligible", "tone": "info", "icon": "Send"},
            {"key": "posted", "label": "Posted", "value": str(posted), "delta": "SAP confirmed", "tone": "success", "icon": "BadgeCheck"},
            {"key": "failed", "label": "Failed", "value": str(failed), "delta": "Requires investigation", "tone": "danger" if failed else "success", "icon": "CircleX"},
            {"key": "success", "label": "Posting success", "value": f"{success_rate}%", "delta": f"{attempted} attempted", "tone": "success" if success_rate >= 95 and attempted else "warning", "icon": "Gauge"},
        ]
        sap_provider = next((item for item in providers if item.get("code") == "sap_s4hana"), None)
        data["sapPosting"] = [
            {"label": "Ready to post", "value": str(ready), "detail": "Approved entries awaiting execution", "tone": "info"},
            {"label": "Posted", "value": str(posted), "detail": "Confirmed SAP document responses", "tone": "success"},
            {"label": "Retryable failures", "value": str(retryable), "detail": "Safe to retry after correction", "tone": "warning" if retryable else "success"},
            {"label": "Non-retryable failures", "value": str(non_retryable), "detail": "Requires configuration or data correction", "tone": "danger" if non_retryable else "success"},
            {"label": "Last SAP connection", "value": str((sap_provider or {}).get("lastTestedAt") or "Not tested"), "detail": str((sap_provider or {}).get("status") or "Not configured"), "tone": "success" if (sap_provider or {}).get("status") == "connected" else "warning"},
        ]

    category_counts = Counter(entry.get("category") or "Unclassified" for entry in entries)
    category_total = sum(category_counts.values())
    data["categoryBreakdown"] = [
        {"category": category, "value": round(count / category_total * 100)}
        for category, count in category_counts.most_common()
    ] if category_total else []
    data["processing"] = [
        {"label": "OCR completed", "value": str(sum(1 for item in files if item.get("ocrStatus") == "completed")), "detail": "Successfully parsed documents", "tone": "success"},
        {"label": "Processing failures", "value": str(sum(1 for item in files if item.get("status") == "validation_failed")), "detail": "Includes validation and processing failures", "tone": "danger" if any(item.get("status") == "validation_failed" for item in files) else "success"},
    ]
    validation_errors = sum(1 for entry in entries for issue in entry.get("issues", []) if issue.get("severity") == "error")
    validation_warnings = sum(1 for entry in entries for issue in entry.get("issues", []) if issue.get("severity") == "warning")
    data["validation"] = [
        {"label": "Blocking errors", "value": str(validation_errors), "detail": "Must be resolved before approval", "tone": "danger" if validation_errors else "success"},
        {"label": "Warnings", "value": str(validation_warnings), "detail": "Require reviewer confirmation", "tone": "warning" if validation_warnings else "success"},
    ]
    data["recentFiles"] = [{"id": file.get("id"), "name": file.get("fileName"), "status": file.get("status"), "createdAt": file.get("createdAt")} for file in files[:5]]
    data["recentEntries"] = [{"id": entry.get("id"), "description": str(entry.get("englishDescription") or entry.get("description") or "")[:240], "category": entry.get("category", ""), "amount": f"{entry.get('currency','')} {entry.get('amount',0)}", "status": entry.get("status", "")} for entry in entries[:5]]
    data["auditActivity"] = get_state(db, scope, "audit", [])[:5]
    return data


@router.get("/analytics/enterprise", dependencies=[Depends(require_frontend_permission("analytics:read"))])
def enterprise_analytics(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = get_state(db, scope, "files", [])
    entries = ensure_entries(db, scope)
    reviews, _ = ensure_review(db, scope)
    postings = get_state(db, scope, "sap_postings", [])
    errors = get_state(db, scope, "errors", [])
    confidences = [float((entry.get("confidence") or {}).get("overall") or 0) for entry in entries]
    average_confidence = sum(confidences) / len(confidences) if confidences else 0
    posted = sum(1 for record in postings if record.get("sapStatus") == "posted")
    failed = sum(1 for record in postings if record.get("sapStatus") == "failed")
    approval_counter = Counter(review.get("status") or "unknown" for review in reviews)
    validation_counter = Counter(entry.get("validationStatus") or "unknown" for entry in entries)

    periods: dict[str, dict] = defaultdict(lambda: {"files": 0, "entries": 0, "ocr": [], "classification": [], "sapSuccess": 0, "sapFailure": 0})
    for file in files:
        period = _date(file.get("createdAt"))
        periods[period]["files"] += 1
        periods[period]["ocr"].append(float(file.get("confidence") or 0))
    for entry in entries:
        period = _date(entry.get("createdAt"))
        periods[period]["entries"] += 1
        periods[period]["classification"].append(float((entry.get("confidence") or {}).get("classification") or 0))
    for record in postings:
        period = _date(record.get("lastAttemptAt") or record.get("approvedAt"))
        if record.get("sapStatus") == "posted":
            periods[period]["sapSuccess"] += 1
        elif record.get("sapStatus") == "failed":
            periods[period]["sapFailure"] += 1

    def avg(values):
        return round(sum(values) / len(values) * 100, 1) if values else 0

    trend = [
        {
            "period": period,
            "files": values["files"],
            "entries": values["entries"],
            "ocrConfidence": avg(values["ocr"]),
            "classificationConfidence": avg(values["classification"]),
            "sapSuccess": values["sapSuccess"],
            "sapFailure": values["sapFailure"],
            "approvalMinutes": 0,
        }
        for period, values in sorted(periods.items())
    ]
    categories = Counter(entry.get("category") or "Unclassified" for entry in entries)
    issue_codes = Counter(issue.get("code") or "UNKNOWN" for entry in entries for issue in entry.get("issues", []))
    failed_types = Counter(file.get("type") or "unknown" for file in files if file.get("status") == "validation_failed")
    metrics = [
        {"key": "files", "label": "Files", "value": str(len(files)), "delta": "Current total", "tone": "info"},
        {"key": "entries", "label": "Entries", "value": str(len(entries)), "delta": "Current total", "tone": "info"},
        {"key": "confidence", "label": "Average confidence", "value": _percent(average_confidence), "delta": "Current average", "tone": "success" if average_confidence >= 0.9 else "warning"},
        {"key": "approved", "label": "Approved", "value": str(approval_counter.get("approved", 0)), "delta": "Approval workflow", "tone": "success"},
        {"key": "validation", "label": "Validation failures", "value": str(validation_counter.get("failed", 0)), "delta": "Blocking entries", "tone": "danger" if validation_counter.get("failed", 0) else "success"},
        {"key": "posting_failed", "label": "Failed postings", "value": str(failed), "delta": f"{posted} posted successfully", "tone": "danger" if failed else "success"},
        {"key": "errors", "label": "Open errors", "value": str(len(errors)), "delta": "Error Center", "tone": "danger" if errors else "success"},
    ]
    return {
        "metrics": metrics,
        "trend": trend,
        "entriesByCategory": [{"label": label, "value": value} for label, value in categories.items()],
        "validationErrors": [{"label": label, "value": value} for label, value in issue_codes.items()],
        "topClients": [{"label": getattr(getattr(current_user, "company", None), "legal_name", "Current company") or "Current company", "value": len(files)}],
        "failedFileTypes": [{"label": label, "value": value} for label, value in failed_types.items()],
    }


@router.get("/audit", dependencies=[Depends(require_frontend_permission("audit:read"))])
def audit_events(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "audit", [])


@router.get("/audit/logs", dependencies=[Depends(require_frontend_permission("audit:read"))])
def audit_logs(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "audit_logs", [])


@router.get("/monitoring/processing-logs", dependencies=[Depends(require_frontend_permission("audit:read"))])
def processing_logs(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "processing_logs", [])


@router.get("/monitoring/errors", dependencies=[Depends(require_frontend_permission("audit:read"))])
def errors(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "errors", [])


@router.post("/monitoring/errors/{error_id}/retry", dependencies=[Depends(require_frontend_permission("audit:read"))])
def retry_error(error_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    values = get_state(db, scope, "errors", [])
    item = require_item(values, error_id)
    item["attempts"] = int(item.get("attempts", 0)) + 1
    item["details"] = {**(item.get("details") or {}), "retryStatus": "queued", "retryAt": datetime.now(timezone.utc).isoformat()}
    set_state(db, scope, "errors", values)
    return {"id": error_id, "status": "queued"}


@router.get("/notifications")
def list_notifications(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "notifications", [])


@router.post("/notifications/{notification_id}/read")
def read_notification(notification_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    notifications = get_state(db, scope, "notifications", [])
    item = require_item(notifications, notification_id)
    item["isRead"] = True
    set_state(db, scope, "notifications", notifications)
    return item


@router.post("/notifications/mark-all-read")
def read_all_notifications(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    notifications = get_state(db, scope, "notifications", [])
    for item in notifications:
        item["isRead"] = True
    set_state(db, scope, "notifications", notifications)
    return {"status": "completed"}
