"""
File Routes
File upload, download, and management endpoints
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from uuid import UUID
import structlog
from io import BytesIO

from app.database import get_db
from app.dependencies import get_current_user
from app.modules.users.models import User
from app.modules.files.service import FileService
from app.modules.files.schemas import (
    FileUploadResponse,
    FileMetadataResponse,
    FileListResponse,
    FilePreviewResponse,
    FileDownloadResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
)
from app.modules.ingestion.service import IngestionService
from app.core.response import success_response

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/test-version")
async def test_version():
    """Test endpoint to verify backend version"""
    return {"version": "FIXED_MINIO_CONFIG_v2", "timestamp": "2026-06-16T01:09:00"}


@router.post("/upload", response_model=FileUploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    batch_id: Optional[str] = Form(None),
    allow_duplicates: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file for processing
    Creates batch if not provided
    """
    if not current_user.tenant_id or not current_user.company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a company",
        )

    logger.info(
        "upload_file_request",
        user_id=str(current_user.id),
        filename=file.filename,
    )

    # Read file content
    file_content = await file.read()

    # Create batch if not provided
    if not batch_id:
        ingestion_service = IngestionService(db)
        batch = ingestion_service.create_batch(
            tenant_id=current_user.tenant_id,
            company_id=current_user.company_id,
            batch_name=f"Upload - {file.filename}",
        )
        batch_id = str(batch.id)

    # Upload file
    file_service = FileService(db)

    try:
        uploaded_file = await file_service.upload_file(
            tenant_id=current_user.tenant_id,
            batch_id=UUID(batch_id),
            filename=file.filename,
            file_content=file_content,
            allow_duplicates=allow_duplicates,
        )

        return FileUploadResponse.from_orm(uploaded_file)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=FileListResponse)
async def list_files(
    page: int = 1,
    page_size: int = 50,
    batch_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List files for current user's company
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info(
        "list_files",
        user_id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
    )

    file_service = FileService(db)

    batch_uuid = UUID(batch_id) if batch_id else None

    files, total = file_service.list_files(
        tenant_id=current_user.tenant_id,
        company_id=current_user.company_id,
        batch_id=batch_uuid,
        status=status,
        page=page,
        page_size=page_size,
    )

    return FileListResponse(
        files=[FileMetadataResponse.from_orm(f) for f in files],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{file_id}", response_model=FileMetadataResponse)
async def get_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get file metadata by ID
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info("get_file", user_id=str(current_user.id), file_id=str(file_id))

    file_service = FileService(db)
    file = file_service.get_file(file_id, current_user.tenant_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return FileMetadataResponse.from_orm(file)


@router.get("/{file_id}/preview", response_model=FilePreviewResponse)
async def get_file_preview(
    file_id: UUID,
    expiration: int = 3600,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get signed preview URL for file
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info("get_file_preview", user_id=str(current_user.id), file_id=str(file_id))

    file_service = FileService(db)
    file = file_service.get_file(file_id, current_user.tenant_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Generate preview URL
    preview_url = await file_service.generate_preview_url(
        file_id, current_user.tenant_id, expiration
    )

    if not preview_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate preview URL",
        )

    # Also generate download URL
    download_url = await file_service.generate_download_url(
        file_id, current_user.tenant_id, expiration
    )

    return FilePreviewResponse(
        file_id=file.id,
        filename=file.original_filename,
        file_type=file.file_type,
        preview_url=preview_url,
        download_url=download_url,
        expires_in=expiration,
    )


@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def get_file_download(
    file_id: UUID,
    expiration: int = 3600,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get signed download URL for file
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info("get_file_download", user_id=str(current_user.id), file_id=str(file_id))

    file_service = FileService(db)
    file = file_service.get_file(file_id, current_user.tenant_id)

    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    # Generate download URL
    download_url = await file_service.generate_download_url(
        file_id, current_user.tenant_id, expiration
    )

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate download URL",
        )

    return FileDownloadResponse(
        file_id=file.id,
        filename=file.original_filename,
        download_url=download_url,
        expires_in=expiration,
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a file
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info("delete_file", user_id=str(current_user.id), file_id=str(file_id))

    file_service = FileService(db)
    success = await file_service.delete_file(file_id, current_user.tenant_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found",
        )

    return success_response(
        data={"file_id": str(file_id)},
        message="File deleted successfully",
    )


@router.post("/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_files(
    request_data: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete multiple files at once
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant",
        )

    logger.info(
        "bulk_delete_files",
        user_id=str(current_user.id),
        file_count=len(request_data.file_ids),
    )

    file_service = FileService(db)

    deleted_count = 0
    failed_count = 0
    failed_ids = []

    for file_id in request_data.file_ids:
        try:
            success = await file_service.delete_file(file_id, current_user.tenant_id)
            if success:
                deleted_count += 1
            else:
                failed_count += 1
                failed_ids.append(file_id)
        except Exception as e:
            logger.error("bulk_delete_file_failed", error=str(e), file_id=str(file_id))
            failed_count += 1
            failed_ids.append(file_id)

    return BulkDeleteResponse(
        deleted_count=deleted_count,
        failed_count=failed_count,
        failed_ids=failed_ids,
    )
