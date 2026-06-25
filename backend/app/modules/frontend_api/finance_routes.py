from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.frontend_api.defaults import ROLE_PERMISSIONS
from app.modules.frontend_api.events import append_audit, append_processing_log
from app.modules.frontend_api.security import (
    get_frontend_user as get_current_user,
    require_frontend_any_permission,
    require_frontend_permission,
)
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import frontend_role, new_id, now_iso, require_item

router = APIRouter()


def _line(kind: str, amount: float, currency: str, gl: str, name: str, memo: str = "Generated accounting line") -> dict:
    return {
        "id": new_id("line"), "type": kind, "glAccount": gl, "accountName": name,
        "amount": round(float(amount or 0), 2), "currency": currency, "memo": memo,
    }


def _accounting_entry(file: dict, amount: float, currency: str, gl_account: str, description: str) -> dict:
    tax = max(0.0, float(file.get("taxAmount") or 0))
    subtotal = float(file.get("subtotal") or 0)
    if subtotal <= 0 and amount >= tax:
        subtotal = amount - tax
    debit_lines = [_line("debit", subtotal if tax > 0 else amount, currency, gl_account, "Expense / source account")]
    if tax > 0:
        debit_lines.append(_line("debit", tax, currency, "141000", "Input tax", "Extracted tax amount"))
    document_date = file.get("invoiceDate") or datetime.now(timezone.utc).date().isoformat()
    return {
        "header": {
            "documentType": "SA", "companyCode": "", "postingDate": datetime.now(timezone.utc).date().isoformat(),
            "documentDate": document_date, "reference": file.get("referenceNumber") or file.get("invoiceNumber") or file.get("id", ""),
            "headerText": description[:50],
        },
        "debitLines": debit_lines,
        "creditLines": [_line("credit", amount, currency, "200000", "Payable / clearing account")],
    }


def _entry(file: dict, index: int) -> dict:
    fields = file.get("structuredFields") or {}
    amount = float(fields.get("total") or file.get("amount") or 0)
    currency = fields.get("currency") or file.get("currency") or "USD"
    description = file.get("extractedText") or file.get("fileName") or "Uploaded financial document"
    description = str(description).strip()[:1000]
    category = file.get("category") or "Expenses"
    subcategory = file.get("subcategory") or "Unclassified"
    gl_account = "610000" if category == "Expenses" else ("400000" if category == "Income" else "100000")
    confidence = float(file.get("confidence") or 0)
    entry = {
        "id": new_id("entry"), "entryId": f"ENT-{index + 1:05d}", "fileId": file.get("id", ""),
        "sourceFile": file.get("fileName", "Uploaded document"), "sourceBatch": file.get("batchId") or "Manual upload",
        "sourcePage": 1, "vendor": fields.get("vendor") or file.get("vendor"), "customer": fields.get("customer") or file.get("customer"),
        "gstVatNumber": fields.get("gstVatNumber") or file.get("gstVatNumber"),
        "originalDescription": str(file.get("extractedText") or description),
        "englishDescription": "",
        "description": description,
        "reference": fields.get("referenceNumber") or file.get("referenceNumber") or file.get("id", ""),
        "referenceNumber": fields.get("referenceNumber") or file.get("referenceNumber") or "",
        "invoiceNumber": fields.get("invoiceNumber") or file.get("invoiceNumber") or "",
        "date": fields.get("invoiceDate") or file.get("invoiceDate") or "",
        "dueDate": fields.get("dueDate") or file.get("dueDate"),
        "amount": amount, "subtotal": fields.get("subtotal") or file.get("subtotal"),
        "taxAmount": fields.get("taxAmount") if fields.get("taxAmount") is not None else file.get("taxAmount"),
        "taxRate": fields.get("taxRate") if fields.get("taxRate") is not None else file.get("taxRate"),
        "taxRates": fields.get("taxRates") or [], "currency": currency, "lineItems": fields.get("lineItems") or file.get("lineItems") or [],
        "category": category, "subcategory": subcategory, "glAccount": gl_account, "glSuggestion": gl_account,
        "sapTCode": "FB50", "postingProcess": "General Ledger Posting", "accountingSoftwareAction": "Create journal entry",
        "operation": "Review and approve", "status": "needs_review", "reviewer": "Unassigned",
        "confidence": {"ocr": float((file.get("ocr") or {}).get("overallConfidence") or confidence), "classification": confidence, "mapping": 0.9, "overall": confidence},
        "classificationReason": file.get("classificationReason") or "Generated from local document processing and routed for human confirmation.",
        "mappingSuggestion": {"sapTCode": "FB50", "postingProcess": "General Ledger Posting", "accountingSoftwareAction": "Create journal entry", "glSuggestion": gl_account, "confidence": 0.9, "reason": "Default company-safe general ledger mapping."},
        "accountingEntry": _accounting_entry(file, amount, currency, gl_account, description),
        "processingStatus": {"ocr": file.get("ocrStatus"), "extraction": file.get("extractionStatus"), "sourceLanguage": file.get("sourceLanguage")},
        "processingIssues": deepcopy(file.get("validationIssues") or []),
        "reviewComments": "", "createdAt": file.get("createdAt") or now_iso(), "updatedAt": now_iso(),
    }
    issues = _validate(entry)
    entry["issues"] = issues
    entry["validationStatus"] = "failed" if any(issue.get("severity") == "error" for issue in issues) else ("warning" if issues else "valid")
    if entry["validationStatus"] == "failed":
        entry["status"] = "validation_failed"
    return entry


def ensure_entries(db: Session, scope: str) -> list[dict]:
    entries = get_state(db, scope, "entries", [])
    files = get_state(db, scope, "files", [])
    by_file = {str(item.get("fileId")): item for item in entries}
    changed = False
    for file in files:
        if int(file.get("entriesExtracted") or 0) <= 0:
            continue
        file_id = str(file.get("id"))
        entry = by_file.get(file_id)
        if entry is None:
            entry = _entry(file, len(entries))
            entries.append(entry); by_file[file_id] = entry; changed = True
        else:
            fields = file.get("structuredFields") or {}
            entry["sourceFile"] = file.get("fileName", entry.get("sourceFile"))
            entry["originalDescription"] = file.get("extractedText") or entry.get("originalDescription", "")
            entry["processingStatus"] = {"ocr": file.get("ocrStatus"), "extraction": file.get("extractionStatus"), "sourceLanguage": file.get("sourceLanguage")}
            entry["processingIssues"] = deepcopy(file.get("validationIssues") or [])
            for key in ("vendor", "customer", "gstVatNumber", "invoiceNumber", "referenceNumber", "dueDate", "subtotal", "taxAmount", "taxRate", "taxRates", "lineItems"):
                if entry.get(key) in (None, "", []) and fields.get(key) not in (None, "", []):
                    entry[key] = deepcopy(fields.get(key))
            if not entry.get("date") and fields.get("invoiceDate"):
                entry["date"] = fields.get("invoiceDate")
            if float(entry.get("amount") or 0) <= 0 and fields.get("total"):
                entry["amount"] = fields.get("total")
            entry["confidence"] = {**(entry.get("confidence") or {}), "ocr": float((file.get("ocr") or {}).get("overallConfidence") or 0), "classification": file.get("confidence", 0), "overall": file.get("confidence", 0)}
            issues = _validate(entry)
            entry["issues"] = issues
            entry["validationStatus"] = "failed" if any(issue.get("severity") == "error" for issue in issues) else ("warning" if issues else "valid")
            changed = True
    valid_file_ids = {str(file.get("id")) for file in files}
    filtered = [entry for entry in entries if str(entry.get("fileId")) in valid_file_ids]
    if len(filtered) != len(entries):
        entries = filtered; changed = True
    if changed or get_state(db, scope, "entries", None) is None:
        set_state(db, scope, "entries", entries)
    return entries


def _validate(candidate: dict) -> list[dict]:
    issues: list[dict] = []
    seen: set[tuple[str, str]] = set()
    def add(code: str, severity: str, message: str, field: str) -> None:
        key = (code, field)
        if key not in seen:
            seen.add(key); issues.append({"code": code, "severity": severity, "message": message, "field": field})

    for issue in candidate.get("processingIssues") or []:
        add(str(issue.get("code") or "PROCESSING_ISSUE"), str(issue.get("severity") or "error"), str(issue.get("message") or "Processing issue"), str(issue.get("field") or "processing"))
    processing = candidate.get("processingStatus") or {}
    for key in ("ocr", "extraction"):
        if processing.get(key) not in {None, "completed"}:
            add(f"{key.upper()}_INCOMPLETE", "error", f"{key.title()} processing is incomplete.", key)
    for field, code, label in (
        ("invoiceNumber", "INVOICE_NUMBER_REQUIRED", "Invoice number"),
        ("vendor", "VENDOR_REQUIRED", "Vendor"),
        ("date", "INVOICE_DATE_REQUIRED", "Invoice date"),
    ):
        if not str(candidate.get(field) or "").strip(): add(code, "error", f"{label} is required.", field)
    if not candidate.get("category") or not candidate.get("subcategory"):
        add("CLASSIFICATION_REQUIRED", "error", "Category and subcategory are required.", "category")
    if not candidate.get("sapTCode"): add("SAP_TCODE_REQUIRED", "error", "SAP T-Code is required.", "sapTCode")
    if not candidate.get("glAccount"): add("GL_REQUIRED", "error", "A GL account is required.", "glAccount")
    amount = float(candidate.get("amount") or 0)
    if amount <= 0: add("AMOUNT_INVALID", "error", "Amount must be greater than zero.", "amount")
    if len(str(candidate.get("currency") or "")) != 3: add("CURRENCY_INVALID", "error", "Currency must use a three-letter ISO code.", "currency")
    if candidate.get("taxAmount") is not None and float(candidate.get("taxAmount") or 0) < 0: add("TAX_AMOUNT_INVALID", "error", "Tax amount cannot be negative.", "taxAmount")
    if candidate.get("taxAmount") not in {None, 0, 0.0} and not candidate.get("gstVatNumber"):
        add("TAX_ID_MISSING", "warning", "A GST/VAT number should be confirmed when tax is present.", "gstVatNumber")
    accounting = candidate.get("accountingEntry") or {}
    debit_lines = accounting.get("debitLines") or []; credit_lines = accounting.get("creditLines") or []
    debit = sum(float(line.get("amount") or 0) for line in debit_lines); credit = sum(float(line.get("amount") or 0) for line in credit_lines)
    if not debit_lines or not credit_lines: add("ACCOUNTING_LINES_REQUIRED", "error", "At least one debit and one credit line are required.", "accountingEntry")
    if abs(debit - credit) >= 0.01: add("ACCOUNTING_UNBALANCED", "error", f"Debit total {debit:.2f} does not equal credit total {credit:.2f}.", "accountingEntry")
    if amount > 0 and abs(debit - amount) >= 0.01: add("ACCOUNTING_AMOUNT_MISMATCH", "error", f"Accounting debit total {debit:.2f} does not equal invoice amount {amount:.2f}.", "accountingEntry")
    line_currencies = {str(line.get("currency") or "") for line in debit_lines + credit_lines if line.get("currency")}
    if line_currencies and line_currencies != {str(candidate.get("currency") or "")}: add("ACCOUNTING_CURRENCY_MISMATCH", "error", "Accounting line currency must match the invoice currency.", "currency")
    return issues


read_entries = Depends(require_frontend_any_permission("entries:read", "entries:manage"))


@router.get("/entries", dependencies=[read_entries])
def list_entries(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ensure_entries(db, scope_for_user(current_user))


@router.get("/entries/validation-issues", dependencies=[read_entries])
def validation_issues(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [entry for entry in ensure_entries(db, scope_for_user(current_user)) if entry.get("issues") or entry.get("validationStatus") in {"failed", "warning"}]


@router.get("/entries/{entry_id}", dependencies=[read_entries])
def get_entry(entry_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return require_item(ensure_entries(db, scope_for_user(current_user)), entry_id)


@router.patch("/entries/{entry_id}", dependencies=[Depends(require_frontend_permission("entries:manage"))])
def update_entry(entry_id: str, patch: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    entries = ensure_entries(db, scope)
    entry = require_item(entries, entry_id)
    old = deepcopy(entry)
    entry.update(deepcopy(patch))
    entry["issues"] = _validate(entry)
    entry["validationStatus"] = "failed" if any(issue.get("severity") == "error" for issue in entry["issues"]) else ("warning" if entry["issues"] else "valid")
    entry["updatedAt"] = now_iso()
    set_state(db, scope, "entries", entries)
    _sync_task_from_entry(db, scope, entry)
    append_audit(db, scope, current_user, "ENTRY_UPDATED", "entry", entry["id"], old_value=old, new_value=entry, metadata={"entryId": entry.get("entryId")})
    return entry


@router.post("/entries/{entry_id}/validate", dependencies=[Depends(require_frontend_permission("entries:manage"))])
def validate_entry(entry_id: str, candidate: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    entries = ensure_entries(db, scope)
    entry = require_item(entries, entry_id)
    issues = _validate(candidate)
    status = "failed" if any(issue["severity"] == "error" for issue in issues) else ("warning" if issues else "valid")
    entry.update(deepcopy(candidate))
    entry["issues"] = issues
    entry["validationStatus"] = status
    entry["updatedAt"] = now_iso()
    if status == "failed":
        entry["status"] = "validation_failed"
    elif entry.get("status") == "validation_failed":
        entry["status"] = "needs_review"
    set_state(db, scope, "entries", entries)
    _sync_task_from_entry(db, scope, entry)
    append_processing_log(db, scope, stage="validation", message=f"Entry {entry.get('entryId')} validation {status}", level="success" if status == "valid" else "warning", job_id=new_id("validation"), file_id=entry.get("fileId"))
    append_audit(db, scope, current_user, "ENTRY_VALIDATED", "entry", entry["id"], new_value={"validationStatus": status, "issues": issues}, metadata={"entryId": entry.get("entryId")})
    return {"validationStatus": status, "issues": issues}


CHECKLIST = [
    ("original_document_reviewed", "Original document reviewed"),
    ("category_confirmed", "Category confirmed"), ("sap_tcode_confirmed", "SAP T-Code confirmed"),
    ("accounting_entry_balanced", "Accounting entry balanced"), ("master_data_confirmed", "Master data confirmed"),
    ("no_duplicate_detected", "No duplicate detected"), ("sap_payload_reviewed", "SAP/accounting payload reviewed"),
]


def _task_status(entry: dict) -> str:
    status = str(entry.get("status") or "needs_review")
    if status in {"approved", "rejected", "changes_requested", "reviewed", "ready_for_approval", "in_review"}:
        return {"reviewed": "ready_for_approval"}.get(status, status)
    if entry.get("validationStatus") == "failed":
        return "validation_failed"
    if float((entry.get("confidence") or {}).get("overall") or 0) < 0.82:
        return "low_confidence"
    return "pending_review"


def _new_task(entry: dict, index: int) -> dict:
    status = _task_status(entry)
    return {
        "id": new_id("review"), "taskId": f"REV-{index + 1:05d}", "entry": deepcopy(entry), "status": status,
        "assignedReviewer": entry.get("assignedTo") or entry.get("reviewer") or "Unassigned", "reviewerGroup": "Finance Reviewers",
        "priority": "high" if status in {"validation_failed", "low_confidence"} else "medium", "dueAt": now_iso(), "reviewerComments": entry.get("reviewComments") or "",
        "checklist": [{"id": key, "label": label, "checked": status == "approved", "required": True} for key, label in CHECKLIST],
        "secondApprovalRequired": float(entry.get("amount") or 0) >= (250000 if entry.get("currency") == "INR" else 25000),
        "secondApprovalReason": "Amount exceeds the configured two-level approval threshold.", "createdAt": now_iso(), "updatedAt": now_iso(),
    }


def ensure_review(db: Session, scope: str) -> tuple[list[dict], list[dict]]:
    tasks = get_state(db, scope, "review_tasks", [])
    history = get_state(db, scope, "review_history", [])
    entries = ensure_entries(db, scope)
    existing_by_entry = {str((task.get("entry") or {}).get("id")): task for task in tasks}
    changed = False
    for entry in entries:
        entry_id = str(entry.get("id"))
        task = existing_by_entry.get(entry_id)
        if task is None:
            task = _new_task(entry, len(tasks))
            tasks.append(task)
            history.insert(0, _history(task, {"id": "system", "name": "Review router", "role": "System"}, "task_created", "status", "entry_extracted", task["status"], "Review task created automatically."))
            existing_by_entry[entry_id] = task
            changed = True
        else:
            task["entry"] = deepcopy(entry)
            if task.get("status") not in {"approved", "rejected", "changes_requested", "second_approval", "in_review"}:
                task["status"] = _task_status(entry)
            task["updatedAt"] = entry.get("updatedAt") or task.get("updatedAt")
    valid_entry_ids = {str(entry.get("id")) for entry in entries}
    filtered = [task for task in tasks if str((task.get("entry") or {}).get("id")) in valid_entry_ids]
    if len(filtered) != len(tasks):
        tasks = filtered
        changed = True
    if changed or get_state(db, scope, "review_tasks", None) is None:
        set_state(db, scope, "review_tasks", tasks)
        set_state(db, scope, "review_history", history)
    return tasks, history


def _history(task: dict, actor: dict, decision: str, field: str = "status", old: str | None = None, new: str | None = None, comments: str | None = None) -> dict:
    return {"id": new_id("history"), "taskId": task["id"], "entryId": task["entry"].get("entryId", task["entry"].get("id", "")), "actorId": actor.get("id", "unknown"), "actor": actor.get("name", "Unknown"), "actorRole": actor.get("role", "Unknown"), "decision": decision, "field": field, "oldValue": old, "newValue": new, "comments": comments, "timestamp": now_iso()}


def _actor(payload: dict, current_user) -> dict:
    supplied = payload.get("actor") or {}
    return {
        "id": supplied.get("id") or str(getattr(current_user, "id", "unknown")),
        "name": supplied.get("name") or getattr(current_user, "full_name", None) or getattr(current_user, "email", "Unknown"),
        "role": supplied.get("role") or frontend_role(current_user),
    }


def _task(tasks: list[dict], task_id: str) -> dict:
    for task in tasks:
        if task_id in {task.get("id"), task.get("taskId"), (task.get("entry") or {}).get("id"), (task.get("entry") or {}).get("entryId")}:
            return task
    raise HTTPException(status_code=404, detail=f"Review task {task_id} was not found")


def _sync_entry_from_task(db: Session, scope: str, task: dict) -> None:
    entries = ensure_entries(db, scope)
    task_entry = task.get("entry") or {}
    entry = next((item for item in entries if str(item.get("id")) == str(task_entry.get("id"))), None)
    if entry is None:
        return
    entry.update(deepcopy(task_entry))
    entry["status"] = task_entry.get("status") or {
        "ready_for_approval": "ready_for_approval",
        "changes_requested": "changes_requested",
    }.get(task.get("status"), task.get("status", entry.get("status")))
    entry["reviewComments"] = task.get("reviewerComments") or entry.get("reviewComments", "")
    entry["updatedAt"] = now_iso()
    set_state(db, scope, "entries", entries)


def _sync_task_from_entry(db: Session, scope: str, entry: dict) -> None:
    tasks = get_state(db, scope, "review_tasks", [])
    for task in tasks:
        if str((task.get("entry") or {}).get("id")) == str(entry.get("id")):
            task["entry"] = deepcopy(entry)
            task["status"] = _task_status(entry)
            task["updatedAt"] = now_iso()
            set_state(db, scope, "review_tasks", tasks)
            return


def _apply_action(task: dict, action: str, actor: dict, comments: str | None, reviewer_id: str | None = None, reviewer_name: str | None = None) -> tuple[bool, str | None, dict | None]:
    old = task.get("status")
    if action == "assign":
        if not reviewer_name:
            return False, "A reviewer must be selected.", None
        previous = task.get("assignedReviewer", "Unassigned")
        task["assignedReviewer"] = reviewer_name
        task["assignedReviewerId"] = reviewer_id
        decision, field, old, new = "assigned", "assignedReviewer", previous, reviewer_name
    elif action == "mark_reviewed":
        for item in task.get("checklist", []):
            if item.get("required"):
                item["checked"] = True
        task["status"] = "ready_for_approval"
        task["entry"]["status"] = "ready_for_approval"
        decision, field, new = "field_changed", "status", "ready_for_approval"
    elif action == "approve":
        missing = [item for item in task.get("checklist", []) if item.get("required") and not item.get("checked")]
        if missing:
            return False, f"{len(missing)} required checklist item(s) are incomplete.", None
        issues = [issue for issue in (task.get("entry") or {}).get("issues", []) if issue.get("severity") == "error"]
        if issues or (task.get("entry") or {}).get("validationStatus") != "valid":
            return False, "Resolve blocking validation errors and run validation before approval.", None
        accounting = (task.get("entry") or {}).get("accountingEntry") or {}
        debit = sum(float(item.get("amount") or 0) for item in accounting.get("debitLines", []))
        credit = sum(float(item.get("amount") or 0) for item in accounting.get("creditLines", []))
        if abs(debit - credit) >= 0.01:
            return False, "The accounting entry is not balanced.", None
        if task.get("secondApprovalRequired") and task.get("status") != "second_approval":
            return False, "Send this high-value task for second approval first.", None
        task["status"] = "approved"
        task["entry"]["status"] = "approved"
        decision, field, new = "approved", "status", "approved"
    elif action == "reject":
        if not (comments or "").strip():
            return False, "A rejection reason is required.", None
        task["status"] = "rejected"
        task["entry"]["status"] = "rejected"
        task["reviewerComments"] = comments
        decision, field, new = "rejected", "status", "rejected"
    elif action == "request_correction":
        if not (comments or "").strip():
            return False, "Correction instructions are required.", None
        task["status"] = "changes_requested"
        task["entry"]["status"] = "changes_requested"
        task["reviewerComments"] = comments
        task["entry"]["reviewComments"] = comments
        decision, field, new = "changes_requested", "status", "changes_requested"
    elif action == "export":
        decision, field, old, new = "exported", "reviewRecord", "Not exported in this action", "Exported"
    else:
        return False, "Unsupported bulk action.", None
    task["updatedAt"] = now_iso()
    return True, None, _history(task, actor, decision, field, str(old) if old is not None else None, str(new) if new is not None else None, comments)


@router.get("/review/tasks", dependencies=[Depends(require_frontend_permission("review:read"))])
def list_tasks(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ensure_review(db, scope_for_user(current_user))[0]


@router.get("/review/tasks/{task_id}", dependencies=[Depends(require_frontend_permission("review:read"))])
def get_task(task_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _task(ensure_review(db, scope_for_user(current_user))[0], task_id)


@router.get("/review/history", dependencies=[Depends(require_frontend_permission("review:read"))])
def get_history(taskId: str | None = Query(None), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    _, history = ensure_review(db, scope_for_user(current_user))
    return [event for event in history if not taskId or taskId in {event.get("taskId"), event.get("entryId")}]


@router.post("/review/tasks/{task_id}/start", dependencies=[Depends(require_frontend_permission("review:edit"))])
def start_review(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    tasks, history = ensure_review(db, scope)
    task = _task(tasks, task_id)
    old = task["status"]
    task["status"] = "in_review"
    task["entry"]["status"] = "in_review"
    task["updatedAt"] = now_iso()
    actor = _actor(payload, current_user)
    history.insert(0, _history(task, actor, "review_started", "status", old, "in_review", "Review started."))
    set_state(db, scope, "review_tasks", tasks)
    set_state(db, scope, "review_history", history)
    _sync_entry_from_task(db, scope, task)
    append_audit(db, scope, current_user, "REVIEW_STARTED", "review", task["id"], old_value=old, new_value="in_review", metadata={"entryId": task["entry"].get("entryId")})
    return task


@router.patch("/review/tasks/{task_id}", dependencies=[Depends(require_frontend_permission("review:edit"))])
def save_review(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    tasks, history = ensure_review(db, scope)
    task = _task(tasks, task_id)
    actor = _actor(payload, current_user)
    task["entry"]["accountingEntry"] = deepcopy(payload.get("accountingEntry") or task["entry"].get("accountingEntry"))
    task["checklist"] = deepcopy(payload.get("checklist") or task.get("checklist"))
    task["reviewerComments"] = payload.get("reviewerComments", task.get("reviewerComments", ""))
    task["entry"]["reviewComments"] = task["reviewerComments"]
    task["updatedAt"] = now_iso()
    if task["status"] in {"pending_review", "ready_for_approval", "low_confidence"}:
        task["status"] = "in_review"
        task["entry"]["status"] = "in_review"
    history.insert(0, _history(task, actor, "field_changed", "review", None, "saved", task.get("reviewerComments") or "Review saved."))
    set_state(db, scope, "review_tasks", tasks)
    set_state(db, scope, "review_history", history)
    _sync_entry_from_task(db, scope, task)
    append_audit(db, scope, current_user, "REVIEW_SAVED", "review", task["id"], new_value={"status": task.get("status"), "comments": task.get("reviewerComments")}, metadata={"entryId": task["entry"].get("entryId")})
    return task


@router.post("/review/tasks/bulk")
def bulk_review(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    action = str(payload.get("action") or "")
    required = {"assign": "review:assign", "approve": "review:approve", "reject": "review:edit", "request_correction": "review:edit", "mark_reviewed": "review:edit", "export": "review:export"}.get(action)
    if required and required not in ROLE_PERMISSIONS.get(frontend_role(current_user), []):
        raise HTTPException(status_code=403, detail=f"Permission denied: {required} required")
    scope = scope_for_user(current_user)
    tasks, history = ensure_review(db, scope)
    actor = _actor(payload, current_user)
    result = {"action": action, "succeeded": [], "failed": []}
    for task_id in payload.get("taskIds") or []:
        try:
            task = _task(tasks, task_id)
        except HTTPException:
            result["failed"].append({"taskId": task_id, "reason": "Task not found."})
            continue
        ok, reason, event = _apply_action(task, action, actor, payload.get("comments"), payload.get("reviewerId"), payload.get("reviewerName"))
        if ok:
            result["succeeded"].append(task["id"])
            if event:
                history.insert(0, event)
            _sync_entry_from_task(db, scope, task)
            append_audit(db, scope, current_user, f"REVIEW_{action.upper()}", "review", task["id"], old_value=event.get("oldValue") if event else None, new_value=event.get("newValue") if event else None, metadata={"entryId": task["entry"].get("entryId"), "comments": payload.get("comments")})
        else:
            result["failed"].append({"taskId": task["id"], "reason": reason})
    set_state(db, scope, "review_tasks", tasks)
    set_state(db, scope, "review_history", history)
    return result


def _single_action(task_id: str, action: str, payload: dict, current_user: Any, db: Session):
    result = bulk_review({**payload, "taskIds": [task_id], "action": action}, current_user, db)
    if result.get("failed"):
        raise HTTPException(status_code=422, detail=result["failed"][0].get("reason") or "Review action could not be completed")
    return result


@router.post("/review/tasks/{task_id}/approve", dependencies=[Depends(require_frontend_permission("review:approve"))])
def approve(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _single_action(task_id, "approve", payload, current_user, db)


@router.post("/review/tasks/{task_id}/reject", dependencies=[Depends(require_frontend_permission("review:edit"))])
def reject(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _single_action(task_id, "reject", payload, current_user, db)


@router.post("/review/tasks/{task_id}/request-changes", dependencies=[Depends(require_frontend_permission("review:edit"))])
def request_changes(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _single_action(task_id, "request_correction", payload, current_user, db)


@router.post("/review/tasks/{task_id}/mark-reviewed", dependencies=[Depends(require_frontend_permission("review:edit"))])
def mark_reviewed_task(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _single_action(task_id, "mark_reviewed", payload, current_user, db)


@router.post("/review/tasks/{task_id}/second-approval", dependencies=[Depends(require_frontend_permission("review:second_approve"))])
def second_approval(task_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    tasks, history = ensure_review(db, scope)
    task = _task(tasks, task_id)
    missing = [item for item in task.get("checklist", []) if item.get("required") and not item.get("checked")]
    if missing:
        raise HTTPException(status_code=422, detail="Complete all required checklist items before requesting second approval.")
    old = task["status"]
    task["status"] = "second_approval"
    task["updatedAt"] = now_iso()
    actor = _actor(payload, current_user)
    history.insert(0, _history(task, actor, "second_approval_requested", "status", old, "second_approval", payload.get("comments")))
    set_state(db, scope, "review_tasks", tasks)
    set_state(db, scope, "review_history", history)
    append_audit(db, scope, current_user, "SECOND_APPROVAL_REQUESTED", "review", task["id"], old_value=old, new_value="second_approval", metadata={"entryId": task["entry"].get("entryId")})
    return task


def _entry_action(entry_id: str, action: str, payload: dict, current_user, db: Session):
    scope = scope_for_user(current_user)
    tasks, _ = ensure_review(db, scope)
    task = _task(tasks, entry_id)
    _single_action(task["id"], action, payload, current_user, db)
    return require_item(ensure_entries(db, scope), entry_id)


@router.post("/entries/{entry_id}/resubmit", dependencies=[Depends(require_frontend_permission("entries:manage"))])
def resubmit_entry(entry_id: str, payload: dict = Body(default={}), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    entries = ensure_entries(db, scope)
    entry = require_item(entries, entry_id)
    entry["issues"] = _validate(entry)
    entry["validationStatus"] = "failed" if any(issue.get("severity") == "error" for issue in entry["issues"]) else ("warning" if entry["issues"] else "valid")
    if entry["validationStatus"] == "failed":
        raise HTTPException(status_code=422, detail="Resolve blocking validation errors before resubmitting for review.")
    old = entry.get("status")
    entry["status"] = "needs_review"
    entry["reviewComments"] = str(payload.get("comments") or entry.get("reviewComments") or "Corrections completed and resubmitted.")
    entry["updatedAt"] = now_iso()
    set_state(db, scope, "entries", entries)
    tasks, history = ensure_review(db, scope)
    task = _task(tasks, entry_id)
    task["entry"] = deepcopy(entry)
    task["status"] = "pending_review"
    task["updatedAt"] = now_iso()
    actor = _actor(payload, current_user)
    history.insert(0, _history(task, actor, "resubmitted", "status", str(old), "pending_review", entry["reviewComments"]))
    set_state(db, scope, "review_tasks", tasks)
    set_state(db, scope, "review_history", history)
    append_audit(db, scope, current_user, "ENTRY_RESUBMITTED", "entry", entry_id, old_value=old, new_value="needs_review")
    return entry


@router.post("/entries/{entry_id}/mark-reviewed", dependencies=[Depends(require_frontend_permission("review:edit"))])
def mark_reviewed_entry(entry_id: str, payload: dict = Body(default={}), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _entry_action(entry_id, "mark_reviewed", payload, current_user, db)


@router.post("/entries/{entry_id}/approve", dependencies=[Depends(require_frontend_permission("review:approve"))])
def approve_entry(entry_id: str, payload: dict = Body(default={}), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _entry_action(entry_id, "approve", payload, current_user, db)


@router.post("/entries/{entry_id}/reject", dependencies=[Depends(require_frontend_permission("review:edit"))])
def reject_entry(entry_id: str, payload: dict = Body(default={}), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _entry_action(entry_id, "reject", payload, current_user, db)


@router.post("/entries/{entry_id}/request-correction", dependencies=[Depends(require_frontend_permission("review:edit"))])
def request_correction_entry(entry_id: str, payload: dict = Body(default={}), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _entry_action(entry_id, "request_correction", payload, current_user, db)
