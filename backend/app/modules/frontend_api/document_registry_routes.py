"""Document Registry — a read-optimized, registry-shaped view over the Document
Extraction workspace ("files" state). Every document that has been bridged into
extraction automatically has a registry entry; there is no separate creation step
and no separate database table — this avoids fragmenting document state across a
third disconnected store on top of the existing Data Intake registry and Files
workspace.

Fields that the source data genuinely does not capture (this pipeline extracts
GST/finance invoices, not customs/shipment documents) are returned as null rather
than fabricated.
"""
from __future__ import annotations

import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.frontend_api.document_routes import _files, delete_file as _delete_file, process_file as _process_file
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, scope_for_user
from app.modules.frontend_api.utils import require_item

router = APIRouter()

EXPORT_COLUMNS = [
    "id", "originalFileName", "documentType", "status", "extractionStatus", "overallConfidence",
    "ocrConfidence", "ocrEngine", "processingTimeSeconds", "totalPages",
    "languageDetected", "uploadedBy", "uploadedAt",
    "invoiceNumber", "vendorName",
]


def _registry_entry(record: dict[str, Any], json_data: dict[str, Any] | None) -> dict[str, Any]:
    ej = json_data or {}
    metrics = ej.get("processing_metrics") or {}
    confidence_details = ej.get("confidence_details") or []
    field_confidence = (
        round(sum(c.get("confidence", 0) for c in confidence_details) / len(confidence_details), 4)
        if confidence_details else None
    )
    validation_results = ej.get("validation_results") or []
    validation_score = (
        round(sum(1 for v in validation_results if v.get("valid")) / len(validation_results), 4)
        if validation_results else None
    )
    ocr_info = record.get("ocr") or {}
    supplier = ej.get("supplier") or {}
    customer = ej.get("customer") or {}
    invoice_details = ej.get("invoice_details") or {}

    raw_status = str(record.get("status") or "")
    extraction_status = str(record.get("extractionStatus") or "")
    normalized_raw_status = raw_status.lower()
    normalized_extraction_status = extraction_status.lower()

    display_status = raw_status or extraction_status or ""
    if normalized_extraction_status == "completed" and normalized_raw_status not in {"validation_failed", "failed"}:
        display_status = "completed"
    elif raw_status:
        display_status = raw_status

    return {
        "id": record.get("id"),
        "originalFileName": record.get("fileName"),
        "documentType": ej.get("document_type") or record.get("type"),
        "sourceChannel": record.get("source"),
        "intakeRegistryId": record.get("intakeRegistryId"),
        "uploadedAt": record.get("uploadedAt"),
        "processedAt": record.get("processingCompletedAt"),
        "uploadedBy": record.get("uploadedByName"),
        "status": display_status or raw_status,
        "extractionStatus": extraction_status or None,
        "ocrEngine": ej.get("ocr_engine") or ocr_info.get("engine") or record.get("extractionMethod"),
        "processingTimeSeconds": metrics.get("processing_time_seconds"),
        "totalPages": (ej.get("metadata") or {}).get("page_count") or ocr_info.get("pageCount"),
        "languageDetected": record.get("sourceLanguage"),
        "overallConfidence": ej.get("overall_confidence") if ej else record.get("confidence"),
        "ocrConfidence": ocr_info.get("overallConfidence"),
        "fieldExtractionConfidence": field_confidence,
        "validationScore": validation_score,
        "invoiceNumber": invoice_details.get("invoice_number"),
        "vendorName": supplier.get("name"),
        "customerName": customer.get("name"),
        # Not produced by this pipeline today (it extracts finance invoices, not
        # customs/shipment paperwork). Left explicitly null rather than guessed.
        "filingNumber": None,
        "shipmentReference": None,
        "country": None,
        "tradeLane": None,
        "registryCreatedAt": record.get("createdAt"),
        "lastUpdatedAt": record.get("updatedAt") or record.get("processingCompletedAt") or record.get("createdAt"),
        "processingJobId": record.get("lastProcessingJobId"),
        "versionNumber": int(record.get("reprocessCount") or 0),
        "checksum": record.get("checksum"),
        "sizeBytes": record.get("sizeBytes"),
    }


def _filtered_entries(
    db: Session,
    current_user: Any,
    *,
    search: str | None = None,
    status_filter: str | None = None,
    ocr_engine: str | None = None,
) -> list[dict[str, Any]]:
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    json_store = get_state(db, scope, "extraction_json_store", {})

    entries = []
    for record in files:
        json_data = (json_store.get(str(record.get("id"))) or {}).get("json")
        entries.append(_registry_entry(record, json_data))

    if search:
        needle = search.lower()
        entries = [
            e for e in entries
            if needle in str(e.get("originalFileName") or "").lower()
            or needle in str(e.get("invoiceNumber") or "").lower()
            or needle in str(e.get("vendorName") or "").lower()
        ]
    if status_filter:
        entries = [e for e in entries if e.get("status") == status_filter]
    if ocr_engine:
        entries = [e for e in entries if e.get("ocrEngine") == ocr_engine]

    entries.sort(key=lambda e: e.get("uploadedAt") or "", reverse=True)
    return entries


@router.get("/document-registry", dependencies=[Depends(require_frontend_permission("files:read"))])
def list_document_registry(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    status: str | None = Query(None),
    ocr_engine: str | None = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = _filtered_entries(db, current_user, search=search, status_filter=status, ocr_engine=ocr_engine)
    total = len(entries)
    start = (page - 1) * page_size
    return {"entries": entries[start : start + page_size], "total": total}


@router.get("/document-registry/{file_id}", dependencies=[Depends(require_frontend_permission("files:read"))])
def get_document_registry_entry(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    record = require_item(files, file_id)
    json_store = get_state(db, scope, "extraction_json_store", {})
    json_data = (json_store.get(str(file_id)) or {}).get("json")

    entry = _registry_entry(record, json_data)
    entry["processingLogs"] = record.get("processingLogs", [])
    entry["ocr"] = record.get("ocr")
    entry["extractedText"] = record.get("extractedText")
    entry["extractedTables"] = record.get("extractedTables")
    entry["extractionJson"] = json_data
    return entry


@router.post("/document-registry/{file_id}/reprocess", dependencies=[Depends(require_frontend_permission("files:process"))])
def reprocess_document_registry_entry(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _process_file(file_id, current_user=current_user, db=db)


@router.delete("/document-registry/{file_id}", status_code=204, dependencies=[Depends(require_frontend_permission("files:manage"))])
def delete_document_registry_entry(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _delete_file(file_id, current_user=current_user, db=db)


def _csv_bytes(entries: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(EXPORT_COLUMNS)
    for entry in entries:
        writer.writerow([entry.get(c, "") if entry.get(c) is not None else "" for c in EXPORT_COLUMNS])
    return buf.getvalue()


@router.get("/document-registry/export/csv", dependencies=[Depends(require_frontend_permission("files:read"))])
def export_document_registry_csv(
    search: str | None = Query(None),
    status: str | None = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entries = _filtered_entries(db, current_user, search=search, status_filter=status)
    content = _csv_bytes(entries)
    return StreamingResponse(
        iter([content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=document_registry.csv"},
    )


@router.get("/document-registry/export/xlsx", dependencies=[Depends(require_frontend_permission("files:read"))])
def export_document_registry_xlsx(
    search: str | None = Query(None),
    status: str | None = Query(None),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from openpyxl import Workbook

    entries = _filtered_entries(db, current_user, search=search, status_filter=status)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Document Registry"
    sheet.append(EXPORT_COLUMNS)
    for entry in entries:
        sheet.append([entry.get(c) if entry.get(c) is not None else "" for c in EXPORT_COLUMNS])

    buf = io.BytesIO()
    workbook.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=document_registry.xlsx"},
    )
