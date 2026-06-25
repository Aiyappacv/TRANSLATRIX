from __future__ import annotations

import hashlib
import logging
import mimetypes
from datetime import datetime
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session

logger = logging.getLogger("translatrix.preview")

from app.config import settings
from app.database import get_db
from app.modules.frontend_api.events import append_audit, append_error, append_processing_log
from app.modules.frontend_api.processing import process_file_record
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import new_id, now_iso, preview_token, require_item, safe_filename, validate_preview_token
router = APIRouter()
UPLOAD_ROOT = Path(getattr(settings, "FRONTEND_UPLOAD_DIR", "/app/data/uploads"))


def preview_kind(filename: str, mime: str) -> str:
    ext = Path(filename).suffix.lower()
    if mime == "application/pdf" or ext == ".pdf":
        return "pdf"
    if mime.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"}:
        return "image"
    if ext in {".csv", ".xlsx", ".xls", ".xlsm"}:
        return "spreadsheet"
    if ext == ".docx":
        return "docx"
    if mime.startswith("text/") or ext in {".txt", ".json", ".xml", ".md"}:
        return "text"
    return "unsupported"


def _uploader(user) -> dict:
    company = getattr(user, "company", None)
    return {
        "id": str(getattr(user, "id", "")),
        "name": str(getattr(user, "full_name", None) or getattr(user, "email", "User")),
        "email": str(getattr(user, "email", "")),
        "role": str(getattr(getattr(user, "role", None), "name", "unknown")),
        "companyId": str(getattr(user, "company_id", "") or ""),
        "companyName": str(getattr(company, "legal_name", "") or ""),
    }


def create_file_record(file_id: str, filename: str, mime: str, size: int, digest: str, content_path: str, user) -> dict:
    now = now_iso()
    kind = preview_kind(filename, mime)
    token = preview_token(file_id)
    uploader = _uploader(user)
    return {
        "id": file_id,
        "name": filename,
        "fileName": filename,
        "type": kind,
        "mimeType": mime,
        "sizeBytes": size,
        "source": "Local upload",
        "batchId": "BATCH-LOCAL",
        "batchName": "Local uploads",
        "status": "uploaded",
        "ocrStatus": "queued",
        "extractionStatus": "queued",
        "entriesExtracted": 0,
        "confidence": 0,
        "sourceLanguage": "Detecting",
        "extractionMethod": "direct_parser" if kind == "spreadsheet" else "gemini-2.5-pro",
        "checksum": digest,
        "createdAt": now,
        "uploadedAt": now,
        "uploadedBy": uploader,
        "uploadedByName": uploader["name"],
        "previewUrl": f"/api/v1/frontend/files/{file_id}/content?token={token}" if kind in {"pdf", "image", "docx", "text"} else None,
        "spreadsheetRows": [],
        "extractedText": "",
        "extractedTables": [],
        "processingLogs": [{
            "id": new_id("log"),
            "step": "Upload",
            "worker": "frontend-api",
            "status": "completed",
            "message": "File stored and queued for automatic processing.",
            "startedAt": now,
            "completedAt": now,
            "retryable": False,
        }],
        "_contentPath": content_path,
    }


def _public(item: dict) -> dict:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def _files(db: Session, scope: str) -> list[dict]:
    return get_state(db, scope, "files", [])


def update_file(db: Session, scope: str, file_id: str, updater):
    files = _files(db, scope)
    item = require_item(files, file_id)
    updater(item)
    set_state(db, scope, "files", files)
    return item


@router.get("/files", dependencies=[Depends(require_frontend_permission("files:read"))])
def list_files(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [_public(item) for item in _files(db, scope_for_user(current_user))]


@router.get("/files/{file_id}", dependencies=[Depends(require_frontend_permission("files:read"))])
def get_file(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _public(require_item(_files(db, scope_for_user(current_user)), file_id))


def _run_pipeline_background(scope: str, file_id: str, current_user: Any) -> None:
    """Run the processing pipeline in a background task with its own DB session."""
    from app.database import SessionLocal
    from app.modules.frontend_api.finance_routes import ensure_entries, ensure_review
    from app.modules.frontend_api.processing import process_file_record
    from app.modules.frontend_api.store import get_state, set_state
    from app.modules.frontend_api.security import get_frontend_user as get_current_user

    db = SessionLocal()
    try:
        files = get_state(db, scope, "files", [])
        item = next((f for f in files if str(f.get("id")) == file_id), None)
        if item is None:
            logger.warning("Background pipeline: file %s not found for scope %s", file_id, scope)
            return

        process_file_record(db, scope, item, current_user)

        for i, f in enumerate(files):
            if str(f.get("id")) == file_id:
                files[i] = dict(item)
                break
        set_state(db, scope, "files", files)

        ensure_entries(db, scope)
        ensure_review(db, scope)
        has_json = item.get("extractionJson") is not None
        logger.info("pipeline_completed file_id=%s status=%s has_extraction_json=%s", file_id, item.get("status"), has_json)
    except Exception as exc:
        logger.error("Background pipeline failed for file %s: %s", file_id, exc)
    finally:
        db.close()


@router.post("/files/upload", status_code=201, dependencies=[Depends(require_frontend_permission("files:upload"))])
async def upload_file(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    scope = scope_for_user(current_user)
    file_id = new_id("file")
    filename = safe_filename(file.filename or "upload.bin")
    data = await file.read()
    max_size = int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024
    if len(data) > max_size:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_FILE_SIZE_MB} MB limit")
    kind = preview_kind(filename, file.content_type or "")
    if kind == "unsupported":
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload PDF, image, DOCX, CSV, XLSX, text, JSON, or XML.")

    scope_dir = UPLOAD_ROOT / hashlib.sha256(scope.encode()).hexdigest()[:16]
    scope_dir.mkdir(parents=True, exist_ok=True)
    path = scope_dir / f"{file_id}_{filename}"
    path.write_bytes(data)
    mime = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    record = create_file_record(file_id, filename, mime, len(data), hashlib.sha256(data).hexdigest(), str(path), current_user)
    files = _files(db, scope)
    files.insert(0, record)
    set_state(db, scope, "files", files)
    append_audit(db, scope, current_user, "FILE_UPLOADED", "file", file_id, new_value={"fileName": filename, "sizeBytes": len(data)}, metadata={"batchId": record["batchId"]})
    append_processing_log(db, scope, stage="file", message=f"{filename} uploaded by {record['uploadedByName']}", level="success", file_id=file_id, batch_id=record["batchId"])

    background_tasks.add_task(_run_pipeline_background, scope, file_id, current_user)
    logger.info("Upload complete for file %s, pipeline scheduled in background", file_id)
    return _public(record)


@router.post("/files/{file_id}/process", dependencies=[Depends(require_frontend_permission("files:process"))])
def process_file(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    item = require_item(files, file_id)
    if item.get("status") == "processing":
        raise HTTPException(
            status_code=409,
            detail="This document is already being processed. Please wait for it to finish before retrying.",
        )
    process_file_record(db, scope, item, current_user, retry_count=1)
    set_state(db, scope, "files", files)
    from app.modules.frontend_api.finance_routes import ensure_entries, ensure_review
    ensure_entries(db, scope)
    ensure_review(db, scope)
    append_audit(db, scope, current_user, "FILE_PROCESSING_STARTED", "file", file_id, new_value={"status": item.get("status")})
    return _public(item)


@router.get("/files/{file_id}/json", dependencies=[Depends(require_frontend_permission("files:read"))])
def get_extraction_json(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the structured extraction JSON for a processed document."""
    from app.modules.frontend_api.json_export_service import retrieve_extraction_json
    scope = scope_for_user(current_user)
    result = retrieve_extraction_json(db, scope, file_id)
    if result is None:
        item = require_item(_files(db, scope), file_id)
        extraction_json = item.get("extractionJson")
        if extraction_json is None:
            raise HTTPException(status_code=404, detail="Extraction JSON not available. Process the document first.")
        return extraction_json
    return result.model_dump_export()


@router.get("/files/{file_id}/download-extraction-summary", dependencies=[Depends(require_frontend_permission("files:read"))])
def download_extraction_summary(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Download the extraction result as a clean JSON containing only the extracted
    document fields — supplier, customer, invoice details, financial summary, line
    items, and extracted tables. No processing metadata, OCR engine info, confidence
    scores, or timestamps are included."""
    import json as json_module
    from app.modules.frontend_api.json_export_service import retrieve_extraction_json, extract_clean_document_data
    scope = scope_for_user(current_user)
    result = retrieve_extraction_json(db, scope, file_id)
    if result is None:
        item = require_item(_files(db, scope), file_id)
        raw = item.get("extractionJson")
        if raw is None:
            raise HTTPException(status_code=404, detail="Extraction JSON not available. Process the document first.")
        data = extract_clean_document_data(raw)
    else:
        data = result.model_dump_clean_fields()

    if not data:
        raise HTTPException(status_code=404, detail="No extracted fields available.")

    pretty = json_module.dumps(data, indent=2, default=str, ensure_ascii=False)
    filename = f"extraction_{file_id[:12]}.json"
    return PlainTextResponse(
        content=pretty,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/files/{file_id}/download-json", dependencies=[Depends(require_frontend_permission("files:read"))])
def download_extraction_json(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    """Download the structured extraction JSON as a .json file.
    
    The exported JSON contains ONLY the extracted document fields — no processing
    metadata, confidence scores, OCR engine info, timestamps, or other system data.
    Null and empty values are stripped.
    """
    import json as json_module
    from app.modules.frontend_api.json_export_service import retrieve_extraction_json, extract_clean_document_data
    scope = scope_for_user(current_user)
    result = retrieve_extraction_json(db, scope, file_id)
    if result is None:
        item = require_item(_files(db, scope), file_id)
        raw = item.get("extractionJson")
        if raw is None:
            raise HTTPException(status_code=404, detail="Extraction JSON not available. Process the document first.")
        data = extract_clean_document_data(raw)
    else:
        data = result.model_dump_clean_fields()

    if not data:
        raise HTTPException(status_code=404, detail="No extracted fields available.")

    pretty = json_module.dumps(data, indent=2, default=str, ensure_ascii=False)
    invoice_details = data.get("invoice_details") or {}
    invoice_number = invoice_details.get("invoice_number", "") or ""
    name_part = f"INV_{invoice_number}" if invoice_number else f"document_extraction_{now_iso()[:8]}"
    filename = f"{name_part}_extracted.json"
    return PlainTextResponse(
        content=pretty,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/files/{file_id}/preview", dependencies=[Depends(require_frontend_permission("files:read"))])
def preview(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_item(_files(db, scope_for_user(current_user)), file_id)
    return {"url": f"/api/v1/frontend/files/{file_id}/content?token={preview_token(file_id)}"}


@router.get("/files/{file_id}/download", dependencies=[Depends(require_frontend_permission("files:read"))])
def download(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = require_item(_files(db, scope_for_user(current_user)), file_id)
    path = Path(str(item.get("_contentPath") or ""))
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return FileResponse(path, media_type=item.get("mimeType") or "application/octet-stream", filename=item.get("fileName") or path.name)


@router.delete("/files/{file_id}", status_code=204, dependencies=[Depends(require_frontend_permission("files:manage"))])
def delete_file(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    from app.modules.frontend_api.json_export_service import delete_extraction_json
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    item = require_item(files, file_id)
    path = Path(str(item.get("_contentPath") or ""))
    files[:] = [value for value in files if str(value.get("id")) != str(file_id)]
    set_state(db, scope, "files", files)
    entries = get_state(db, scope, "entries", [])
    removed_entry_ids = [str(entry.get("id")) for entry in entries if str(entry.get("fileId")) == str(file_id)]
    entries = [entry for entry in entries if str(entry.get("fileId")) != str(file_id)]
    set_state(db, scope, "entries", entries)
    tasks = get_state(db, scope, "review_tasks", [])
    set_state(db, scope, "review_tasks", [task for task in tasks if str((task.get("entry") or {}).get("fileId")) != str(file_id)])
    postings = get_state(db, scope, "sap_postings", [])
    set_state(db, scope, "sap_postings", [record for record in postings if str(record.get("entryId")) not in removed_entry_ids])
    delete_extraction_json(db, scope, file_id)
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    append_audit(db, scope, current_user, "FILE_DELETED", "file", file_id, old_value={"fileName": item.get("fileName")})
    return Response(status_code=204)


@router.get("/files/{file_id}/content", include_in_schema=False)
def content(file_id: str, token: str = Query(...), db: Session = Depends(get_db)):
    validate_preview_token(file_id, token)
    logger.info("Preview requested for file %s", file_id)
    from app.modules.frontend_api.models import FrontendState
    rows = db.query(FrontendState).filter(FrontendState.namespace == "files").all()
    logger.debug("Found %d namespace rows for file_id=%s", len(rows), file_id)
    for row in rows:
        item = next((value for value in (row.payload or []) if value.get("id") == file_id), None)
        if item:
            content_path = str(item.get("_contentPath") or "")
            mime = item.get("mimeType")
            name = item.get("fileName")
            logger.info("File %s found in scope=%s: path=%s mime=%s", file_id, row.scope_key, content_path, mime)
            path = Path(content_path)
            if not path.exists():
                logger.error("File %s: stored content path does not exist on disk: %s", file_id, content_path)
                raise HTTPException(status_code=404, detail="Stored file not found")
            logger.info("File %s: serving content (size=%d, mime=%s)", file_id, path.stat().st_size, mime)
            return FileResponse(path, media_type=mime, filename=name)
    logger.warning("File %s not found in any namespace row", file_id)
    raise HTTPException(status_code=404, detail="File not found")


@router.get("/files/{file_id}/page-image", include_in_schema=False)
def page_image(file_id: str, page: int = Query(1, ge=1), token: str = Query(...), db: Session = Depends(get_db)):
    validate_preview_token(file_id, token)
    logger.info("Page image requested for file=%s page=%d", file_id, page)
    from app.modules.frontend_api.models import FrontendState
    rows = db.query(FrontendState).filter(FrontendState.namespace == "files").all()
    for row in rows:
        item = next((value for value in (row.payload or []) if value.get("id") == file_id), None)
        if item:
            content_path = str(item.get("_contentPath") or "")
            path = Path(content_path)
            if not path.exists():
                logger.error("Page image: file %s path not found: %s", file_id, content_path)
                raise HTTPException(status_code=404, detail="Stored file not found")
            ext = path.suffix.lower()
            if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}:
                logger.info("Page image: serving image directly")
                return FileResponse(path, media_type=item.get("mimeType"))
            if ext == ".pdf":
                try:
                    from app.modules.frontend_api.pdf_renderer import render_page
                    img_bytes, total_pages = render_page(path, page)
                    logger.info("Page image: rendered PDF page %d/%d (%d bytes)", page, total_pages, len(img_bytes))
                    from fastapi.responses import Response as FastAPIResponse
                    return FastAPIResponse(content=img_bytes, media_type="image/png", headers={"X-Page-Count": str(total_pages)})
                except IndexError as exc:
                    raise HTTPException(status_code=404, detail=str(exc))
                except RuntimeError as exc:
                    raise HTTPException(status_code=501, detail=str(exc))
                except Exception as exc:
                    logger.error("Page image: error rendering page %d: %s", page, str(exc))
                    raise HTTPException(status_code=500, detail="Failed to render PDF page")
            logger.warning("Page image: unsupported file type for page rendering: %s", ext)
            raise HTTPException(status_code=415, detail="Page image rendering is not supported for this file type")
    logger.warning("Page image: file %s not found", file_id)
    raise HTTPException(status_code=404, detail="File not found")


@router.post("/files/{file_id}/ocr/retry", dependencies=[Depends(require_frontend_permission("files:process"))])
def retry_ocr(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = process_file(file_id, current_user, db)
    return {"id": file_id, "status": item.get("ocrStatus", "completed")}


@router.post("/files/{file_id}/ocr/cloud-fallback", dependencies=[Depends(require_frontend_permission("files:process"))])
def cloud_ocr(file_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    item = require_item(files, file_id)
    message = "Cloud OCR credentials are not configured. Use local processing or configure a cloud OCR provider."
    item.setdefault("processingLogs", []).insert(0, {"id": new_id("log"), "step": "Cloud OCR", "worker": "cloud-adapter", "status": "failed", "message": message, "startedAt": now_iso(), "completedAt": now_iso(), "errorDetails": "Configure Azure Document Intelligence or AWS Textract credentials.", "retryable": True})
    set_state(db, scope, "files", files)
    append_processing_log(db, scope, stage="ocr", message=message, level="error", job_id=file_id, file_id=file_id, batch_id=item.get("batchId"))
    append_error(db, scope, category="ocr", code="CLOUD_OCR_NOT_CONFIGURED", message=message, entity_type="file", entity_id=file_id, retryable=True, details={"fileName": item.get("fileName")})
    append_audit(db, scope, current_user, "CLOUD_OCR_FAILED", "file", file_id, status="failed", new_value={"reason": "credentials_not_configured"})
    raise HTTPException(status_code=422, detail=message)


@router.patch("/files/{file_id}/tables/{table_id}", dependencies=[Depends(require_frontend_permission("files:process"))])
def save_table(file_id: str, table_id: str, payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    files = _files(db, scope)
    item = require_item(files, file_id)
    table = next((table for table in item.setdefault("extractedTables", []) if table.get("id") == table_id), None)
    if table is None:
        raise HTTPException(status_code=404, detail="Extracted table not found")
    table["rows"] = payload.get("rows") or []
    set_state(db, scope, "files", files)
    append_audit(db, scope, current_user, "EXTRACTED_TABLE_CORRECTED", "file", file_id, new_value={"tableId": table_id})
    return {"id": file_id, "tableId": table_id, "status": "saved"}


@router.post("/files/{file_id}/steps/{step}/retry", dependencies=[Depends(require_frontend_permission("files:process"))])
def retry_step(file_id: str, step: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = process_file(file_id, current_user, db)
    return {"id": file_id, "step": step, "status": item.get("status", "completed")}
