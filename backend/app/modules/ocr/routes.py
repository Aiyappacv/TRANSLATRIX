"""
OCR Routes
API endpoints for OCR processing
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
import structlog

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.ocr.service import OCRService, OCRError
from app.modules.ocr.schemas import OCRRequest, OCRResponse, OCRStatusResponse
from app.modules.users.models import User
from app.modules.files.service import FileService

logger = structlog.get_logger(__name__)
router = APIRouter()
ocr_service = OCRService()


@router.post("/{file_id}/ocr", response_model=dict)
@require_permissions(["files:read", "files:process"])
async def process_file_ocr(
    file_id: UUID,
    request: OCRRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Perform OCR on a file

    Permissions required: files:read, files:process
    """
    try:
        logger.info(
            "ocr_request",
            file_id=file_id,
            provider=request.provider,
            user_id=current_user.id,
        )

        # Create FileService instance with db session
        file_service = FileService(db)

        result = await ocr_service.process_file(
            db=db,
            file_id=file_id,
            tenant_id=current_user.tenant_id,
            file_service=file_service,
            provider=request.provider,
            language=request.language,
            force_reprocess=request.force_reprocess,
        )

        # Get pages
        pages = ocr_service.get_ocr_pages(db, result.id)

        response_data = OCRResponse.from_orm(result)
        response_data.pages = pages

        return success_response(
            data=response_data,
            message="OCR processing completed successfully"
        )

    except ValueError as e:
        logger.warning("file_not_found", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except OCRError as e:
        logger.error("ocr_failed", file_id=file_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/{file_id}/ocr", response_model=dict)
@require_permissions(["files:read"])
async def get_ocr_result(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get OCR result for a file

    Permissions required: files:read
    """
    result = ocr_service.get_ocr_result(
        db=db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OCR result not found"
        )

    # Get pages
    pages = ocr_service.get_ocr_pages(db, result.id)

    response_data = OCRResponse.from_orm(result)
    response_data.pages = pages

    return success_response(
        data=response_data,
        message="OCR result retrieved successfully"
    )


@router.get("/{file_id}/ocr/status", response_model=dict)
@require_permissions(["files:read"])
async def get_ocr_status(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get OCR processing status

    Permissions required: files:read
    """
    result = ocr_service.get_ocr_result(
        db=db,
        file_id=file_id,
        tenant_id=current_user.tenant_id,
    )

    if not result:
        return success_response(
            data=OCRStatusResponse(
                status="not_started",
                message="OCR not yet initiated"
            ),
            message="Status retrieved"
        )

    progress = None
    if result.status.value == "completed":
        progress = 100
    elif result.status.value == "processing":
        progress = 50

    return success_response(
        data=OCRStatusResponse(
            status=result.status.value,
            progress=progress,
            message=result.error_message if result.error_message else None
        ),
        message="Status retrieved"
    )
