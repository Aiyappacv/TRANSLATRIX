"""
Ingestion Routes
File ingestion and batch management endpoints
"""
import uuid
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Body, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from uuid import UUID
import structlog
import json
from datetime import datetime, timezone

from app.database import get_db
from app.dependencies import get_current_user, require_permission
from app.modules.users.models import User
from app.modules.files.models import IngestedFile
from app.modules.ingestion.service import IngestionService
from app.modules.ingestion.schemas import (
    SharedLinkValidateRequest,
    SharedLinkValidateResponse,
    SharedLinkCreateRequest,
    SharedLinkResponse,
    SharedLinkListResponse,
    SharedLinkSyncRequest,
    BatchCreateRequest,
    BatchResponse,
    BatchListResponse,
    BatchDetailResponse,
    FileDiscoveryResponse,
    PreprocessingResult,
    LakeTierRecord,
    ProcessingAuditResponse,
    DedupResult,
    PreviewInfo,
    PreviewPage,
    ExtractionJobResponse,
    ExtractionResult,
    ExtractedField,
    ExportRequest,
    ExportResponse,
    ExportFile,
)
from app.core.response import success_response, error_response
from app.modules.ingestion.tiered_storage import TieredStorageManager, LakeTier
from app.modules.ingestion.preprocessing import PreprocessingPipeline
from app.modules.ingestion.deduplication import DeduplicationEngine
from app.modules.storage.service import get_storage_adapter

logger = structlog.get_logger(__name__)

router = APIRouter()


# Shared Link Endpoints
@router.post("/shared-links/validate", response_model=SharedLinkValidateResponse)
async def validate_shared_link(
    request_data: SharedLinkValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a shared link before adding as a source
    Checks accessibility and returns file count/size
    """
    logger.info(
        "validate_shared_link",
        user_id=str(current_user.id),
        source_type=request_data.source_type,
    )

    service = IngestionService(db)
    result = await service.validate_shared_link(
        url=request_data.url,
        source_type=request_data.source_type,
        credentials=request_data.credentials,
    )

    return result


@router.post("/shared-links", response_model=SharedLinkResponse)
async def create_shared_link(
    request_data: SharedLinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new shared link source for file ingestion
    Requires files:write permission
    """
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company",
        )

    logger.info(
        "create_shared_link",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
        source_type=request_data.source_type,
    )

    service = IngestionService(db)
    source = service.create_shared_link_source(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
        name=request_data.name,
        source_type=request_data.source_type,
        url=request_data.url,
        credentials=request_data.credentials,
        config=request_data.config,
    )

    return SharedLinkResponse.from_orm(source)


@router.get("/shared-links", response_model=SharedLinkListResponse)
async def list_shared_links(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all shared link sources for the current company
    """
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company",
        )

    logger.info(
        "list_shared_links",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    service = IngestionService(db)
    sources, total = service.list_shared_link_sources(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
    )

    return SharedLinkListResponse(
        sources=[SharedLinkResponse.from_orm(s) for s in sources],
        total=total,
    )


@router.post("/shared-links/{source_id}/sync", response_model=FileDiscoveryResponse)
async def sync_shared_link(
    source_id: UUID,
    request_data: SharedLinkSyncRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync files from a shared link source
    Discovers available files without downloading
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info(
        "sync_shared_link",
        user_id=str(current_user.id),
        source_id=str(source_id),
    )

    service = IngestionService(db)

    try:
        result = await service.sync_shared_link(
            source_id=source_id,
            tenant_id=current_user.tenant_id,
            file_types=request_data.file_types,
            recursive=request_data.recursive,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


# ====== Preprocessing Endpoints ======

@router.post("/files/{file_id}/preprocess", response_model=PreprocessingResult)
async def preprocess_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    if not file_record.original_filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File has no filename")

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


# ====== Deduplication Endpoints ======

@router.post("/files/{file_id}/deduplicate", response_model=DedupResult)
async def deduplicate_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

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


# ====== Preview Endpoints ======

@router.get("/files/{file_id}/preview", response_model=PreviewInfo)
async def get_file_preview(
    file_id: UUID,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    from app.modules.frontend_api.utils import preview_token
    token = preview_token(str(file_id), current_user.tenant_id)
    from datetime import datetime, timedelta, timezone
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()

    storage = await get_storage_adapter()
    service = IngestionService(db)
    preview_data = await service.generate_preview(
        file_record=file_record,
        storage=storage,
        page=page,
    )
    return PreviewInfo(
        fileId=str(file_id),
        filename=file_record.original_filename or "unknown",
        contentType=file_record.content_type or "application/octet-stream",
        sizeBytes=file_record.file_size or 0,
        totalPages=preview_data.get("totalPages", 1),
        pages=[
            PreviewPage(
                pageNumber=p["pageNumber"],
                imageUrl=p["imageUrl"],
                width=p.get("width", 0),
                height=p.get("height", 0),
            )
            for p in preview_data.get("pages", [])
        ],
        previewToken=token,
        expiresAt=expires_at,
    )


# ====== Extraction Endpoints ======

@router.post("/files/{file_id}/extract", response_model=ExtractionJobResponse)
async def extract_file_fields(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    file_record = db.query(IngestedFile).filter(IngestedFile.id == file_id, IngestedFile.tenant_id == current_user.tenant_id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = await get_storage_adapter()
    service = IngestionService(db)
    result = await service.extract_fields(
        file_record=file_record,
        storage=storage,
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id or current_user.tenant_id,
    )
    return ExtractionJobResponse(
        jobId=str(file_id),
        fileId=str(file_id),
        status="completed",
        result=result,
    )


# ====== JSON Export Endpoints ======

@router.post("/export", response_model=ExportResponse)
async def export_as_json(
    request_data: ExportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    service = IngestionService(db)
    export_result = await service.export_files(
        file_ids=request_data.fileIds,
        tenant_id=current_user.tenant_id,
        storage=storage,
        include_raw_text=request_data.includeRawText,
        include_metadata=request_data.includeMetadata,
        include_confidence=request_data.includeConfidence,
    )
    return ExportResponse(
        exportId=str(uuid.uuid4()),
        exportedAt=datetime.now(timezone.utc).isoformat(),
        totalFiles=len(export_result.get("files", [])),
        files=[ExportFile(**f) for f in export_result.get("files", [])],
        jsonPayload=json.dumps(export_result, default=str, indent=2),
    )


# ====== Tier Audit Endpoints ======

@router.get("/files/{file_id}/tiers", response_model=List[LakeTierRecord])
async def get_file_tiers(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    storage = await get_storage_adapter()
    tiered = TieredStorageManager(db, storage)
    records = tiered.get_tier_records(file_id)
    return [LakeTierRecord(
        id=str(r.id),
        fileId=str(r.file_id),
        tier=r.tier.value if hasattr(r.tier, 'value') else str(r.tier),
        storageKey=r.storage_key,
        checksum=r.checksum,
        contentType=r.content_type,
        sizeBytes=r.size_bytes,
        metadataJson=r.metadata_json,
        createdAt=r.created_at,
    ) for r in records]


@router.get("/files/{file_id}/audit", response_model=List[ProcessingAuditResponse])
async def get_file_audit_log(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User must belong to a tenant")

    from app.modules.ingestion.tiered_storage import ProcessingAudit
    records = (
        db.query(ProcessingAudit)
        .filter(ProcessingAudit.file_id == file_id)
        .order_by(ProcessingAudit.created_at)
        .all()
    )
    return [ProcessingAuditResponse(
        id=str(r.id),
        fileId=str(r.file_id),
        step=r.step.value if hasattr(r.step, 'value') else str(r.step),
        status=r.status,
        message=r.message,
        durationMs=r.duration_ms,
        metadataJson=r.metadata_json,
        createdAt=r.created_at,
    ) for r in records]


# Batch Endpoints
@router.post("/batches", response_model=BatchResponse)
async def create_batch(
    request_data: BatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new ingestion batch
    Groups files for processing
    """
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company",
        )

    logger.info(
        "create_batch",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    service = IngestionService(db)
    batch = service.create_batch(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
        source_id=request_data.source_id,
        batch_name=request_data.batch_name,
    )

    return BatchResponse.from_orm(batch)


@router.get("/batches", response_model=BatchListResponse)
async def list_batches(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all batches for the current company
    """
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company",
        )

    logger.info(
        "list_batches",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    service = IngestionService(db)
    batches, total = service.list_batches(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
        page=page,
        page_size=page_size,
    )

    return BatchListResponse(
        batches=[BatchResponse.from_orm(b) for b in batches],
        total=total,
    )


@router.get("/batches/{batch_id}", response_model=BatchDetailResponse)
async def get_batch(
    batch_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a batch including files
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info(
        "get_batch",
        user_id=str(current_user.id),
        batch_id=str(batch_id),
    )

    service = IngestionService(db)
    batch = service.get_batch(batch_id, current_user.tenant_id)

    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Batch not found",
        )

    # Get batch files
    files = service.get_batch_files(batch_id, current_user.tenant_id)

    return BatchDetailResponse(
        batch=BatchResponse.from_orm(batch),
        files=[
            {
                "id": str(f.id),
                "filename": f.original_filename,
                "file_type": f.file_type,
                "file_size": f.file_size,
                "status": f.status.value,
                "created_at": f.created_at.isoformat(),
            }
            for f in files
        ],
    )
