from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import uuid
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from time import perf_counter
from typing import Optional
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlparse, urlunparse
from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.modules.frontend_api.events import append_audit, append_error, append_processing_log
from app.modules.frontend_api.security import get_frontend_user as get_current_user, require_frontend_permission
from app.modules.frontend_api.store import get_state, scope_for_user, set_state
from app.modules.frontend_api.utils import new_id, now_iso, require_item, safe_filename
from app.modules.files.models import IngestedFile
from app.modules.ingestion.tiered_storage import TieredStorageManager, ProcessingAudit
from app.modules.ingestion.preprocessing import PreprocessingPipeline
from app.modules.ingestion.deduplication import DeduplicationEngine
from app.modules.ingestion.service import IngestionService
from app.modules.storage.service import get_storage_adapter

router = APIRouter()
SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".csv", ".xlsx", ".xlsm", ".docx", ".txt", ".json", ".xml"}


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append(str(href))


def _supported(name: str) -> bool:
    return Path(urlparse(name).path).suffix.lower() in SUPPORTED_EXTENSIONS


def _discovery_item(name: str, source_url: str, size: int = 0, mime: str | None = None) -> dict:
    filename = safe_filename(unquote(Path(urlparse(name).path).name or Path(urlparse(source_url).path).name or "remote-file"))
    supported = _supported(filename)
    return {
        "id": new_id("discovered"),
        "fileName": filename,
        "path": urlparse(source_url).path or "/",
        "mimeType": mime or mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "sizeBytes": int(size or 0),
        "status": "supported" if supported else "unsupported",
        "reason": None if supported else "File type is not supported by the processing pipeline.",
        "discoveredAt": now_iso(),
        "sourceUrl": source_url,
    }


def _local_discovery(db: Session, scope: str) -> list[dict]:
    return [
        {
            "id": new_id("discovered"),
            "fileName": item.get("fileName"),
            "path": item.get("fileName"),
            "mimeType": item.get("mimeType"),
            "sizeBytes": item.get("sizeBytes", 0),
            "status": "supported",
            "reason": None,
            "discoveredAt": now_iso(),
            "fileId": item.get("id"),
        }
        for item in get_state(db, scope, "files", [])
    ]


def _normalize_public_source_url(source_type: str, url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    source = source_type.lower()
    if "dropbox" in host or source == "dropbox":
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["dl"] = "1"
        return urlunparse(parsed._replace(query=urlencode(query)))
    if "drive.google.com" in host or source == "google drive":
        match = re.search(r"/file/d/([^/]+)", parsed.path)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        file_id = match.group(1) if match else query.get("id")
        if file_id:
            return f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    if "1drv.ms" in host or "onedrive" in host or source == "onedrive":
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["download"] = "1"
        return urlunparse(parsed._replace(query=urlencode(query)))
    if "sharepoint.com" in host or source == "sharepoint":
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["download"] = "1"
        return urlunparse(parsed._replace(query=urlencode(query)))
    return url


def _public_url_discovery(url: str, source_type: str = "Manual URL") -> tuple[bool, list[dict], str | None, int]:
    started = perf_counter()
    url = _normalize_public_source_url(source_type, url)
    try:
        with httpx.Client(follow_redirects=True, timeout=10.0, headers={"User-Agent": "TRANSLATRIX-PRO/1.0"}) as client:
            response = client.get(url)
        latency = int((perf_counter() - started) * 1000)
        response.raise_for_status()
        final_url = str(response.url)
        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        disposition = response.headers.get("content-disposition", "")
        match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition, re.IGNORECASE)
        hinted_name = unquote(match.group(1).strip('"')) if match else Path(urlparse(final_url).path).name
        if _supported(hinted_name) or (content_type and content_type not in {"text/html", "application/xhtml+xml", "application/xml", "text/xml"}):
            return True, [_discovery_item(hinted_name or "remote-file", final_url, len(response.content), content_type)], None, latency

        discovered: list[dict] = []
        body = response.text
        if content_type in {"application/xml", "text/xml"} or body.lstrip().startswith("<?xml"):
            try:
                root = ElementTree.fromstring(body)
                for element in root.iter():
                    tag = element.tag.rsplit("}", 1)[-1].lower()
                    if tag in {"key", "name", "blobname"} and element.text and _supported(element.text):
                        discovered.append(_discovery_item(element.text, urljoin(final_url, element.text)))
            except ElementTree.ParseError:
                pass
        else:
            parser = LinkCollector()
            parser.feed(body)
            seen: set[str] = set()
            for href in parser.links:
                absolute = urljoin(final_url, href)
                if absolute in seen or not _supported(absolute):
                    continue
                seen.add(absolute)
                discovered.append(_discovery_item(absolute, absolute))
                if len(discovered) >= 100:
                    break
        warning = None if discovered else "The source is reachable, but no supported public files were exposed. Private cloud folders require provider credentials."
        return True, discovered, warning, latency
    except Exception as exc:
        return False, [], f"Source discovery failed: {exc}", int((perf_counter() - started) * 1000)


def validate_payload(payload: dict, db: Session, scope: str) -> dict:
    source_type = str(payload.get("sourceType") or "Manual URL")
    url = str(payload.get("url") or "").strip()
    if source_type == "Local Upload":
        discovered = _local_discovery(db, scope)
        accessible, warning, latency = True, None, 0
    elif not url or urlparse(url).scheme not in {"http", "https"}:
        discovered, accessible, warning, latency = [], False, "Enter a valid HTTPS public URL. SFTP, private S3, Azure Blob, Drive, OneDrive, SharePoint, and Dropbox require configured connector credentials.", 0
    else:
        accessible, discovered, warning, latency = _public_url_discovery(url, source_type)
        if payload.get("authenticationType") == "None" and source_type not in {"Manual URL", "Local Upload"}:
            warning = warning or "Only publicly accessible files can be discovered without provider credentials."
    supported = [item for item in discovered if item["status"] == "supported"]
    unsupported = [item for item in discovered if item["status"] != "supported"]
    return {
        "accessible": accessible,
        "filesFound": len(discovered),
        "supportedFilesCount": len(supported),
        "unsupportedFilesCount": len(unsupported),
        "estimatedProcessingTime": f"Approximately {max(1, len(supported) * 2)} minute(s)" if supported else "Available after file discovery",
        "securityWarning": warning,
        "latencyMs": latency,
        "discoveredFiles": discovered,
    }


@router.get("/shared-links", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def list_links(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "shared_links", [])


@router.get("/shared-links/{link_id}", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def get_link(link_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return require_item(get_state(db, scope_for_user(current_user), "shared_links", []), link_id)


@router.post("/shared-links/validate", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def validate_link(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return validate_payload(payload, db, scope_for_user(current_user))


@router.post("/shared-links", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def create_link(payload: dict = Body(...), current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    validation = validate_payload(payload, db, scope)
    url = str(payload.get("url") or "")
    host = urlparse(url).hostname or "local-upload"
    item = {
        "id": new_id("src"), "clientName": payload.get("clientName") or getattr(getattr(current_user, "company", None), "legal_name", "Company"),
        "name": payload.get("name") or "Untitled source", "provider": payload.get("sourceType") or "Manual URL", "sourceType": payload.get("sourceType") or "Manual URL",
        "url": url, "authenticationType": payload.get("authenticationType") or "None", "folderPath": payload.get("folderPath") or "/", "fileFilters": payload.get("fileFilters") or "*",
        "schedule": payload.get("schedule") or "Manual", "defaultCompanyCode": payload.get("defaultCompanyCode") or "", "defaultCurrency": payload.get("defaultCurrency") or "USD",
        "defaultReviewerGroup": payload.get("defaultReviewerGroup") or "", "defaultAccountingIntegration": payload.get("defaultAccountingIntegration") or "", "allowedDomain": payload.get("allowedDomain") or host,
        "status": "active" if validation["accessible"] else "failed", "lastSyncAt": now_iso(), "filesDiscovered": validation["filesFound"], "owner": current_user.email, "validation": validation,
    }
    links = get_state(db, scope, "shared_links", [])
    links.insert(0, item)
    set_state(db, scope, "shared_links", links)
    append_audit(db, scope, current_user, "SHARED_LINK_CREATED", "integration", item["id"], new_value={"name": item["name"], "sourceType": item["sourceType"], "filesDiscovered": item["filesDiscovered"]})
    return item


def _revalidate(link: dict, db: Session, scope: str) -> dict:
    validation = validate_payload(link, db, scope)
    link["validation"] = validation
    link["filesDiscovered"] = validation["filesFound"]
    link["lastSyncAt"] = now_iso()
    link["status"] = "active" if validation["accessible"] else "failed"
    return link


@router.post("/shared-links/{link_id}/validate", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def revalidate_link(link_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    links = get_state(db, scope, "shared_links", [])
    link = require_item(links, link_id)
    _revalidate(link, db, scope)
    set_state(db, scope, "shared_links", links)
    append_audit(db, scope, current_user, "SHARED_LINK_VALIDATED", "integration", link_id, new_value={"filesDiscovered": link["filesDiscovered"], "status": link["status"]})
    return link["validation"]


@router.post("/shared-links/{link_id}/sync", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def sync_link(link_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    links = get_state(db, scope, "shared_links", [])
    link = require_item(links, link_id)
    _revalidate(link, db, scope)
    set_state(db, scope, "shared_links", links)
    append_processing_log(db, scope, stage="batch", message=f"Shared source {link.get('name')} synchronized; {link.get('filesDiscovered')} files discovered", level="success" if link.get("status") == "active" else "error", job_id=link_id)
    return link


@router.post("/shared-links/sync-all", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def sync_all(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    links = get_state(db, scope, "shared_links", [])
    synced_at = now_iso()
    for link in links:
        _revalidate(link, db, scope)
    set_state(db, scope, "shared_links", links)
    append_audit(db, scope, current_user, "SHARED_LINKS_SYNCHRONIZED", "integration", "all", new_value={"count": len(links), "syncedAt": synced_at})
    return {"status": "completed", "syncedAt": synced_at}


def _download_discovered(item: dict, scope: str, user, db: Session, batch_id: str) -> dict | None:
    source_url = item.get("sourceUrl")
    if not source_url:
        return None
    try:
        with httpx.Client(follow_redirects=True, timeout=20.0, headers={"User-Agent": "TRANSLATRIX-PRO/1.0"}) as client:
            response = client.get(source_url)
        response.raise_for_status()
        max_size = int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024
        if len(response.content) > max_size:
            raise ValueError(f"Remote file exceeds {settings.MAX_FILE_SIZE_MB} MB")
        from app.modules.frontend_api.document_routes import UPLOAD_ROOT, create_file_record
        from app.modules.frontend_api.processing import process_file_record
        file_id = new_id("file")
        filename = safe_filename(item.get("fileName") or "remote-file")
        scope_dir = UPLOAD_ROOT / hashlib.sha256(scope.encode()).hexdigest()[:16]
        scope_dir.mkdir(parents=True, exist_ok=True)
        path = scope_dir / f"{file_id}_{filename}"
        path.write_bytes(response.content)
        mime = response.headers.get("content-type", "").split(";", 1)[0] or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        record = create_file_record(file_id, filename, mime, len(response.content), hashlib.sha256(response.content).hexdigest(), str(path), user)
        record.update({"source": "Shared link", "batchId": batch_id, "batchName": batch_id})
        process_file_record(db, scope, record, user)
        return record
    except Exception as exc:
        append_error(db, scope, category="integration", code="REMOTE_FILE_IMPORT_FAILED", message=str(exc), entity_type="file", entity_id=item.get("id", "remote"), retryable=True, details={"sourceUrl": source_url})
        return None


def create_batch_for_link(db: Session, scope: str, link: dict, current_user) -> dict:
    now = now_iso()
    batch_id = new_id("batch")
    discovered = [item for item in (link.get("validation") or {}).get("discoveredFiles", []) if item.get("status") == "supported"]
    files_state = get_state(db, scope, "files", [])
    attached: list[dict] = []
    failed = 0
    if link.get("sourceType") == "Local Upload":
        ids = {str(item.get("fileId")) for item in discovered if item.get("fileId")}
        attached = [item for item in files_state if str(item.get("id")) in ids]
        for item in attached:
            item["batchId"] = batch_id
            item["batchName"] = link.get("name", "Shared source")
    else:
        for discovered_item in discovered[:20]:
            imported = _download_discovered(discovered_item, scope, current_user, db, batch_id)
            if imported:
                files_state.insert(0, imported)
                attached.append(imported)
            else:
                failed += 1
    set_state(db, scope, "files", files_state)
    from app.modules.frontend_api.finance_routes import ensure_entries, ensure_review
    entries = ensure_entries(db, scope)
    ensure_review(db, scope)
    attached_ids = {str(item.get("id")) for item in attached}
    batch_entries = [entry for entry in entries if str(entry.get("fileId")) in attached_ids]
    status = "completed" if attached and not failed else ("validation_failed" if failed else "completed")
    batch = {
        "id": batch_id, "client": link.get("clientName", "Company"), "sourceName": link.get("name", "Source"), "sourceType": link.get("sourceType", "Manual URL"), "provider": link.get("provider", "Manual URL"),
        "createdAt": now, "startedAt": now, "completedAt": now, "status": status, "totalFiles": len(discovered), "processedFiles": len(attached), "failedFiles": failed,
        "extractedEntries": len(batch_entries), "pendingReview": sum(1 for entry in batch_entries if entry.get("status") in {"needs_review", "reviewed", "ready_for_approval", "in_review"}), "postedEntries": sum(1 for entry in batch_entries if entry.get("status") == "sap_posted"),
        "files": len(attached), "entries": len(batch_entries), "failed": failed, "duplicateCount": 0, "discoveredFiles": discovered,
        "entryPreviews": [{"id": entry.get("id"), "document": entry.get("sourceFile"), "vendor": entry.get("vendor") or "", "category": entry.get("category", "Expense").rstrip("s"), "amount": entry.get("amount", 0), "currency": entry.get("currency", "USD"), "confidence": (entry.get("confidence") or {}).get("overall", 0), "status": entry.get("status", "needs_review")} for entry in batch_entries],
        "errors": [],
        "timeline": [
            {"id": new_id("step"), "label": "Source validated", "description": f"{len(discovered)} supported file(s) discovered.", "status": "completed", "timestamp": now, "actor": "API"},
            {"id": new_id("step"), "label": "File import and processing", "description": f"{len(attached)} processed; {failed} failed.", "status": "completed" if not failed else "warning", "timestamp": now, "actor": "Document pipeline"},
        ],
        "audit": [{"id": new_id("batch_audit"), "actor": getattr(current_user, "email", "API"), "action": "BATCH_CREATED", "details": "Batch created from shared-link source.", "createdAt": now}],
    }
    batches = get_state(db, scope, "batches", [])
    batches.insert(0, batch)
    set_state(db, scope, "batches", batches)
    append_audit(db, scope, current_user, "BATCH_CREATED", "integration", batch_id, new_value={"sourceId": link.get("id"), "totalFiles": len(discovered), "processedFiles": len(attached), "failedFiles": failed}, metadata={"batchId": batch_id})
    append_processing_log(db, scope, stage="batch", message=f"Batch {batch_id} created with {len(attached)} processed file(s)", level="success" if not failed else "warning", job_id=batch_id, batch_id=batch_id)
    return batch


@router.post("/shared-links/{source_id}/create-batch", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def create_batch(source_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    links = get_state(db, scope, "shared_links", [])
    link = require_item(links, source_id)
    _revalidate(link, db, scope)
    set_state(db, scope, "shared_links", links)
    if not link.get("validation", {}).get("supportedFilesCount"):
        raise HTTPException(status_code=422, detail="No supported files were discovered. Revalidate the source or configure provider credentials.")
    batch = create_batch_for_link(db, scope, link, current_user)
    return {"batchId": batch["id"], "status": batch["status"]}


@router.get("/batches", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def list_batches(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return get_state(db, scope_for_user(current_user), "batches", [])


@router.get("/batches/{batch_id}", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def get_batch(batch_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    return require_item(get_state(db, scope_for_user(current_user), "batches", []), batch_id)


@router.post("/batches/retry-failed", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def retry_failed(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    batches = get_state(db, scope, "batches", [])
    retried = 0
    for batch in batches:
        if batch.get("status") in {"validation_failed", "sap_failed"} or batch.get("failedFiles", 0) > 0:
            batch["status"] = "processing"
            batch.setdefault("timeline", []).append({"id": new_id("step"), "label": "Retry requested", "description": "Failed batch items were queued for retry.", "status": "processing", "timestamp": now_iso(), "actor": getattr(current_user, "email", "User")})
            retried += 1
    set_state(db, scope, "batches", batches)
    return {"retried": retried, "status": "processing" if retried else "completed"}


@router.post("/batches/{batch_id}/retry", dependencies=[Depends(require_frontend_permission("ingestion:manage"))])
def retry_batch(batch_id: str, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    scope = scope_for_user(current_user)
    batches = get_state(db, scope, "batches", [])
    batch = require_item(batches, batch_id)
    batch["status"] = "processing"
    batch["startedAt"] = now_iso()
    batch.setdefault("timeline", []).append({"id": new_id("step"), "label": "Retry requested", "description": "The batch was queued for retry.", "status": "processing", "timestamp": now_iso(), "actor": getattr(current_user, "email", "User")})
    set_state(db, scope, "batches", batches)
    append_audit(db, scope, current_user, "BATCH_RETRIED", "integration", batch_id, new_value={"status": "processing"}, metadata={"batchId": batch_id})
    return {"id": batch_id, "status": "processing"}


# ====== Preprocessing ======

@router.post("/files/{file_id}/preprocess")
async def preprocess_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    if not file_record.original_filename:
        raise HTTPException(status_code=400, detail="File has no filename")

    storage = await get_storage_adapter()
    tiered = TieredStorageManager(db, storage)
    pipeline = PreprocessingPipeline(db, tiered)

    content_bytes = await storage.download_file(file_record.storage_path) if file_record.storage_path else b""
    result = await pipeline.run(
        file_content=content_bytes,
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id or current_user.tenant_id,
        file_id=file_id,
        filename=file_record.original_filename,
        content_type=file_record.content_type or "application/octet-stream",
        checksum=file_record.checksum or "",
    )
    return result


# ====== Deduplication ======

@router.post("/files/{file_id}/deduplicate")
async def deduplicate_file(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    storage = await get_storage_adapter()
    tiered = TieredStorageManager(db, storage)
    dedup = DeduplicationEngine(db, tiered)

    content_bytes = await storage.download_file(file_record.storage_path) if file_record.storage_path else b""
    result = await dedup.check_duplicate(
        file_id=file_id,
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id or current_user.tenant_id,
        filename=file_record.original_filename or "unknown",
        content_bytes=content_bytes,
    )
    return result.to_dict()


# ====== Preview ======

@router.get("/files/{file_id}/preview-pages")
async def get_file_preview(
    file_id: str,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    storage = await get_storage_adapter()
    service = IngestionService(db)
    preview_data = await service.generate_preview(file_record=file_record, storage=storage, page=page)

    return {
        "fileId": str(file_id),
        "filename": file_record.original_filename or "unknown",
        "contentType": file_record.content_type or "application/octet-stream",
        "sizeBytes": file_record.file_size or 0,
        "totalPages": preview_data.get("totalPages", 1),
        "pages": [
            {"pageNumber": p["pageNumber"], "imageUrl": p["imageUrl"], "width": p.get("width", 0), "height": p.get("height", 0)}
            for p in preview_data.get("pages", [])
        ],
        "previewToken": str(uuid.uuid4()),
        "expiresAt": (datetime.now(timezone.utc)).isoformat(),
    }


# ====== Extraction ======

@router.post("/files/{file_id}/extract")
async def extract_file_fields(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")

    storage = await get_storage_adapter()
    service = IngestionService(db)
    result = await service.extract_fields(
        file_record=file_record,
        storage=storage,
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id or current_user.tenant_id,
    )
    return {
        "jobId": str(file_id),
        "fileId": str(file_id),
        "status": "completed",
        "result": {
            "fileId": result.fileId,
            "filename": result.filename,
            "fields": [{"name": f.name, "value": f.value, "confidence": f.confidence, "pageNumber": f.pageNumber, "bbox": f.bbox} for f in result.fields],
            "rawText": result.rawText,
            "confidence": result.confidence,
            "processingTimeMs": result.processingTimeMs,
            "ocrEngine": result.ocrEngine,
        },
        "error": None,
    }


# ====== Export ======

@router.post("/export")
async def export_as_json(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    file_ids = payload.get("fileIds", [])
    include_raw_text = payload.get("includeRawText", True)
    include_metadata = payload.get("includeMetadata", True)
    include_confidence = payload.get("includeConfidence", False)

    storage = await get_storage_adapter()
    service = IngestionService(db)
    export_result = await service.export_files(
        file_ids=file_ids,
        tenant_id=current_user.tenant_id,
        storage=storage,
        include_raw_text=include_raw_text,
        include_metadata=include_metadata,
        include_confidence=include_confidence,
    )
    return {
        "exportId": str(uuid.uuid4()),
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "totalFiles": len(export_result.get("files", [])),
        "files": export_result.get("files", []),
        "jsonPayload": json.dumps(export_result, default=str, indent=2),
    }


# ====== Tier / Audit ======

@router.get("/files/{file_id}/tiers")
async def get_file_tiers(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    tiered = TieredStorageManager(db, storage)
    records = tiered.get_tier_records(file_id)
    return [
        {
            "id": str(r.id),
            "fileId": str(r.file_id),
            "tier": r.tier.value if hasattr(r.tier, "value") else str(r.tier),
            "storageKey": r.storage_key,
            "checksum": r.checksum,
            "contentType": r.content_type,
            "sizeBytes": r.size_bytes,
            "metadataJson": r.metadata_json,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


@router.get("/files/{file_id}/audit")
async def get_file_audit_log(
    file_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=400, detail="User must belong to a tenant")

    records = (
        db.query(ProcessingAudit)
        .filter(ProcessingAudit.file_id == file_id)
        .order_by(ProcessingAudit.created_at)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "fileId": str(r.file_id),
            "step": r.step.value if hasattr(r.step, "value") else str(r.step),
            "status": r.status,
            "message": r.message,
            "durationMs": r.duration_ms,
            "metadataJson": r.metadata_json,
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
