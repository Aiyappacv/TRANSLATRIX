from __future__ import annotations

import asyncio
import traceback
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.modules.users.models import User
from app.modules.ingestion.data_intake_service import DataIntakeService
from app.modules.ingestion.data_intake_schemas import (
    IntakeRegistryEntry,
    IntakeRegistryListResponse,
    CheckDuplicateResponse,
    PreviewResponse,
    ExtractNavigationResponse,
    DeleteResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    IntakeEventResponse,
    BatchProgressResponse,
    RetryExtractionResponse,
)
from app.modules.ingestion.data_intake_models import SourceChannel, IntakeStatus, IntakeRegistry
from app.modules.ingestion.worker import get_worker
from app.modules.storage.service import get_storage_adapter

logger = structlog.get_logger(__name__)

router = APIRouter()


def _get_service(db: Session = Depends(get_db)) -> DataIntakeService:
    import asyncio
    storage = asyncio.run(get_storage_adapter())
    return DataIntakeService(db, storage)


@router.post("/data-ingestion/upload", response_model=dict)
async def upload_file(
    file: UploadFile = File(...),
    source_channel: str = Form("portal"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload phase only: validate -> stream to storage -> register ->
    return. Heavy enrichment (checksum, duplicate detection, page count,
    language, orientation, embeddings) runs entirely in the background
    metadata pipeline — see _process_metadata_job."""
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a company")

    try:
        channel = SourceChannel(source_channel)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid source channel: {source_channel}")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    logger.info("data_ingestion_upload_attempt", user_id=str(current_user.id), tenant_id=str(current_user.tenant_id), company_id=str(current_user.company_id), filename=file.filename)
    try:
        entry = await service.register_upload(current_user.tenant_id, current_user.company_id, file, channel)
    except ValueError as exc:
        logger.warning("data_ingestion_register_failed", error=str(exc), filename=file.filename)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        import traceback as _tb
        tb = _tb.format_exc()
        logger.error("data_ingestion_register_exception", error=str(exc), traceback=tb)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register upload: {exc}")

    logger.info("data_ingestion_registered", entry_id=str(entry.id), status=entry.status, filename=entry.original_filename)

    worker = await get_worker("metadata")
    worker.enqueue(
        job_type="metadata_process",
        tenant_id=current_user.tenant_id,
        payload={"entry_id": entry.id, "tenant_id": str(current_user.tenant_id)},
        handler=_process_metadata_job,
        max_retries=3,
    )

    return {
        "entry": entry.model_dump(),
        "status": entry.status,
        "message": "File uploaded and registered. Metadata processing started in the background.",
    }


@router.post("/data-ingestion/upload/batch", response_model=dict)
async def upload_batch(
    files: list[UploadFile] = File(...),
    source_channel: str = Form("portal"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk upload: every file is streamed to storage concurrently and
    registered in a single DB transaction (DataIntakeService.register_upload_batch),
    so the response returns as soon as storage + registration finish — not
    after every file's metadata has been computed."""
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a company")
    if len(files) > settings.MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch exceeds the maximum of {settings.MAX_BATCH_SIZE} files",
        )

    try:
        channel = SourceChannel(source_channel)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid source channel: {source_channel}")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    entries, total, accepted = await service.register_upload_batch(
        current_user.tenant_id, current_user.company_id, files, channel
    )

    batch_id = str(uuid.uuid4())
    worker = await get_worker("metadata")
    for entry in entries:
        worker.enqueue(
            job_type="metadata_process",
            tenant_id=current_user.tenant_id,
            payload={"entry_id": entry.id, "tenant_id": str(current_user.tenant_id), "batch_id": batch_id},
            handler=_process_metadata_job,
            max_retries=3,
        )

    return {
        "batch_id": batch_id,
        "total": total,
        "accepted": accepted,
        "entries": [e.model_dump() for e in entries],
        "message": f"{accepted} of {total} files uploaded and registered",
    }


@router.get("/data-ingestion/registry", response_model=IntakeRegistryListResponse)
async def list_registry(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    entries, total = await service.list_registry(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        source_filter=source,
        search=search,
    )
    return IntakeRegistryListResponse(entries=entries, total=total)


@router.get("/data-ingestion/registry/{entry_id}", response_model=IntakeRegistryEntry)
async def get_registry_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    entry = service.get_registry_entry(entry_id, current_user.tenant_id)
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registry entry not found")
    return entry


@router.get("/data-ingestion/registry/{entry_id}/preview", response_model=PreviewResponse)
async def get_registry_preview(
    entry_id: uuid.UUID,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    try:
        preview = await service.get_preview(entry_id, current_user.tenant_id, page)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/data-ingestion/registry/{entry_id}/preview/page/{page_number}", include_in_schema=False)
async def get_registry_preview_page(
    entry_id: uuid.UUID,
    page_number: int,
    db: Session = Depends(get_db),
):
    from pathlib import Path
    from app.modules.files.models import IngestedFile
    from app.modules.frontend_api.pdf_renderer import render_page

    storage = await get_storage_adapter()

    entry = db.query(IntakeRegistry).filter(
        IntakeRegistry.id == entry_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registry entry not found")

    ingested = db.query(IngestedFile).filter(IngestedFile.id == entry.file_id).first() if entry.file_id else None
    if not ingested or not ingested.storage_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stored file not found")

    content_bytes = await storage.download_file(ingested.storage_path)
    ext = Path(entry.original_filename).suffix.lower()

    if ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"}:
        from fastapi.responses import Response as FastAPIResponse
        return FastAPIResponse(content=content_bytes, media_type=entry.mime_type or "image/png")

    if ext == ".pdf":
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content_bytes)
            tmp_path = tmp.name
        try:
            img_bytes, total_pages = render_page(Path(tmp_path), page_number)
            from fastapi.responses import Response as FastAPIResponse
            return FastAPIResponse(
                content=img_bytes,
                media_type="image/png",
                headers={"X-Page-Count": str(total_pages)},
            )
        except IndexError:
            raise HTTPException(status_code=404, detail="Page not found")
        except RuntimeError:
            raise HTTPException(status_code=501, detail="PDF renderer not available")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    raise HTTPException(status_code=415, detail="Preview not supported for this file type")


@router.post("/data-ingestion/registry/{entry_id}/extract", response_model=ExtractNavigationResponse)
async def prepare_extraction(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    try:
        result = await service.prepare_extraction(entry_id, current_user.tenant_id, current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error: {e}")


@router.delete("/data-ingestion/registry/{entry_id}", response_model=DeleteResponse)
async def delete_registry_entry(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    try:
        result = await service.hard_delete(entry_id, current_user.tenant_id, current_user)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/data-ingestion/registry/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_registry_entries(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    try:
        result = await service.bulk_hard_delete(
            [uuid.UUID(eid) for eid in request.entry_ids],
            current_user.tenant_id,
            current_user,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/data-ingestion/check-duplicate", response_model=CheckDuplicateResponse)
async def check_duplicate(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    return await service.check_duplicate(
        tenant_id=current_user.tenant_id,
        filename=file.filename or "unknown",
        content=content,
    )


@router.get("/data-ingestion/registry/{entry_id}/events", response_model=list[IntakeEventResponse])
async def get_registry_events(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)
    try:
        return service.get_events(entry_id, current_user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/data-ingestion/batches/{batch_id}/progress", response_model=BatchProgressResponse)
async def get_batch_progress(
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    from app.modules.ingestion.worker import get_batch_progress_all_pools
    return await get_batch_progress_all_pools(batch_id)


@router.post("/data-ingestion/registry/{entry_id}/retry-extraction", response_model=RetryExtractionResponse)
async def retry_extraction(
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = DataIntakeService(db, storage)

    registry = db.query(IntakeRegistry).filter(
        IntakeRegistry.id == entry_id,
        IntakeRegistry.tenant_id == current_user.tenant_id,
    ).first()
    if not registry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registry entry not found")
    if registry.status != IntakeStatus.FAILED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only failed entries can be retried")

    metadata = dict(registry.processing_metadata or {})
    metadata["retry_count"] = metadata.get("retry_count", 0) + 1
    metadata["retry_of"] = str(entry_id)
    registry.processing_metadata = metadata

    # The two-stage pipeline can fail at either point — retry whichever
    # stage actually failed rather than always jumping to extraction (which
    # would run on a document that never got its checksum/page-count/etc.
    # if metadata processing itself was what failed).
    if "metadata_error" in metadata and not registry.checksum:
        registry.status = IntakeStatus.UPLOADED
        db.commit()
        service._log_event(
            registry.id, "retry_metadata", "pending",
            f"Metadata processing retry queued for: {registry.original_filename}",
            {"retry_count": metadata["retry_count"]},
        )
        worker = await get_worker("metadata")
        worker.enqueue(
            job_type="metadata_process",
            tenant_id=current_user.tenant_id,
            payload={"entry_id": str(registry.id), "tenant_id": str(current_user.tenant_id)},
            handler=_process_metadata_job,
            max_retries=3,
        )
        return RetryExtractionResponse(entry_id=str(registry.id), status="queued", message="Metadata processing retry queued")

    registry.status = IntakeStatus.READY_FOR_EXTRACTION
    db.commit()

    service._log_event(
        registry.id,
        "retry_extraction",
        "pending",
        f"Extraction retry queued for: {registry.original_filename}",
        {"retry_count": metadata["retry_count"]},
    )

    worker = await get_worker("extraction")
    worker.enqueue(
        job_type="extract_document",
        tenant_id=current_user.tenant_id,
        payload={
            "entry_id": str(registry.id),
            "tenant_id": str(current_user.tenant_id),
            "company_id": str(current_user.company_id) if current_user.company_id else str(current_user.tenant_id),
            "file_id": str(registry.file_id) if registry.file_id else "",
            "source_user_id": str(current_user.id) if current_user.id else None,
        },
        handler=_process_extract_job,
        max_retries=3,
    )

    return RetryExtractionResponse(
        entry_id=str(registry.id),
        status="queued",
        message="Extraction retry queued",
    )


# ── Background Job Handlers ─────────────────────────────────


async def _process_metadata_job(
    entry_id: str,
    tenant_id: str,
    batch_id: Optional[str] = None,
):
    """Stage 1 of the background pipeline: checksum, MIME, page count,
    language, orientation, exact-duplicate check. On success, chains into
    the independent embedding-detection job. On failure, marks the entry
    FAILED with the error recorded — never leaves it stuck mid-pipeline."""
    from app.database import SessionLocal
    from app.modules.ingestion.data_intake_service import DataIntakeService

    db = SessionLocal()
    try:
        storage = await get_storage_adapter()
        service = DataIntakeService(db, storage)
        await service.run_metadata_processing(UUID(entry_id))
    except Exception as exc:
        logger.error("metadata_job_failed", entry_id=entry_id, error=str(exc), traceback=traceback.format_exc())
        try:
            registry = db.query(IntakeRegistry).filter(IntakeRegistry.id == UUID(entry_id)).first()
            if registry:
                registry.status = IntakeStatus.FAILED
                registry.processing_metadata = dict(registry.processing_metadata or {})
                registry.processing_metadata["metadata_error"] = str(exc)
                db.commit()
        except Exception:
            logger.warning("metadata_job_failure_cleanup_failed", entry_id=entry_id)
        raise
    else:
        worker = await get_worker("metadata")
        worker.enqueue(
            job_type="embedding_detect",
            tenant_id=UUID(tenant_id),
            payload={"entry_id": entry_id, "tenant_id": tenant_id},
            handler=_process_embedding_job,
            max_retries=3,
        )
    finally:
        db.close()


async def _process_embedding_job(entry_id: str, tenant_id: str):
    """Stage 2 (independent, non-blocking): semantic duplicate detection.
    The document is already READY_FOR_EXTRACTION by the time this runs, so
    failures here (including sentence-transformers/faiss simply not being
    installed) are logged and otherwise swallowed — per spec, worker
    failures must never affect an already-uploaded document."""
    from app.database import SessionLocal
    from app.modules.ingestion.data_intake_service import DataIntakeService

    db = SessionLocal()
    try:
        storage = await get_storage_adapter()
        service = DataIntakeService(db, storage)
        await service.run_embedding_detection(UUID(entry_id))
    except Exception as exc:
        logger.warning("embedding_job_failed", entry_id=entry_id, error=str(exc))
    finally:
        db.close()


async def _process_extract_job(
    entry_id: str,
    tenant_id: str,
    company_id: str = "",
    file_id: str = "",
    batch_id: Optional[str] = None,
    file_index: int = 0,
    source_user_id: Optional[str] = None,
):
    from app.database import SessionLocal
    from app.modules.ingestion.data_intake_service import DataIntakeService
    from app.modules.ingestion.data_intake_models import IntakeRegistry as IRModel, IntakeStatus

    db = SessionLocal()
    try:
        storage = await get_storage_adapter()
        service = DataIntakeService(db, storage)

        tenant_uuid = UUID(tenant_id)
        registry = db.query(IRModel).filter(
            IRModel.id == UUID(entry_id),
            IRModel.tenant_id == tenant_uuid,
        ).first()
        if not registry:
            logger.warning("extract_job_registry_not_found entry_id=%s", entry_id)
            return

        if registry.status in (IntakeStatus.EXTRACTED,):
            logger.info("extract_job_already_done entry_id=%s", entry_id)
            return

        registry.status = IntakeStatus.EXTRACTING
        db.commit()

        service._log_event(
            registry.id,
            "extraction_started",
            "processing",
            f"Extraction started for: {registry.original_filename}",
        )

        worker_user = _resolve_worker_user(db, tenant_id, company_id, source_user_id)
        await service._bridge_to_extraction_workspace(registry, worker_user)

        registry.status = IntakeStatus.EXTRACTED
        registry.processed_at = datetime.utcnow()
        db.commit()

        service._log_event(
            registry.id,
            "extraction_completed",
            "completed",
            f"Extraction completed: {registry.original_filename}",
        )

    except Exception as exc:
        logger.error("background_extract_failed entry_id=%s error=%s", entry_id, exc)
        try:
            registry = db.query(IRModel).filter(IRModel.id == UUID(entry_id)).first()
            if registry:
                registry.status = IntakeStatus.FAILED
                registry.processing_metadata = dict(registry.processing_metadata or {})
                registry.processing_metadata["extraction_error"] = str(exc)
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def _resolve_worker_user(
    db: Session,
    tenant_id: str,
    company_id: str,
    source_user_id: Optional[str] = None,
):
    from app.modules.users.models import User
    if source_user_id:
        user = db.query(User).filter(User.id == UUID(source_user_id)).first()
        if user:
            return user
    from types import SimpleNamespace
    return SimpleNamespace(
        id=str(uuid.uuid4()),
        tenant_id=UUID(tenant_id) if tenant_id else UUID(int=0),
        company_id=UUID(company_id) if company_id else UUID(int=0),
        is_super_admin=False,
        email="system@translatrix.ai",
        full_name="System Worker",
    )
