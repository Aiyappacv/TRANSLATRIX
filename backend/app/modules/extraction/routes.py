"""
Extraction Routes
API endpoints for content extraction
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
import structlog

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response, error_response
from app.modules.extraction.service import ExtractionService, ExtractionError
from app.modules.extraction.schemas import ExtractionRequest, ExtractionResponse, ExtractionStatusResponse
from app.modules.users.models import User

logger = structlog.get_logger(__name__)
router = APIRouter()
extraction_service = ExtractionService()


@router.post("/{file_id}/extract", response_model=dict)
@require_permissions(["files:read", "files:process"])
async def extract_file_content(
    file_id: UUID,
    request: ExtractionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Extract content from a file

    Permissions required: files:read, files:process
    """
    try:
        logger.info(
            "extract_file_request",
            file_id=file_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
        )

        result = await extraction_service.extract_file(
            db=db,
            file_id=file_id,
            tenant_id=current_user.tenant_id,
            use_ocr=request.use_ocr,
            extract_tables=request.extract_tables,
            extract_metadata=request.extract_metadata,
            force_reprocess=request.force_reprocess,
        )

        return success_response(
            data=ExtractionResponse.from_orm(result),
            message="File extraction completed successfully"
        )

    except ValueError as e:
        logger.warning("file_not_found", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ExtractionError as e:
        logger.error("extraction_failed", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{file_id}/extract", response_model=dict)
@require_permissions(["files:read"])
async def get_extraction_result(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get extraction result for a file

    Permissions required: files:read
    """
    result = extraction_service.get_extraction_result(
        db=db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extraction result not found"
        )

    return success_response(
        data=ExtractionResponse.from_orm(result),
        message="Extraction result retrieved successfully"
    )


@router.get("/{file_id}/extract/status", response_model=dict)
@require_permissions(["files:read"])
async def get_extraction_status(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get extraction processing status

    Permissions required: files:read
    """
    result = extraction_service.get_extraction_result(
        db=db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if not result:
        return success_response(
            data=ExtractionStatusResponse(
                status="not_started",
                message="Extraction not yet initiated"
            ),
            message="Status retrieved"
        )

    progress = None
    if result.status.value == "completed":
        progress = 100
    elif result.status.value == "processing":
        progress = 50

    return success_response(
        data=ExtractionStatusResponse(
            status=result.status.value,
            progress=progress,
            message=result.error_message if result.error_message else None
        ),
        message="Status retrieved"
    )
