"""Validation Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.validation.service import ValidationService
from app.modules.validation.schemas import ValidationResultResponse
from app.modules.users.models import User

router = APIRouter()
validation_service = ValidationService()


@router.post("/entries/{entry_id}/validate", response_model=dict)
@require_permissions(["entries:read"])
async def validate_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Validate a financial entry"""
    results = validation_service.validate_entry(db, entry_id, current_user.tenant_id)
    return success_response(
        data=[ValidationResultResponse.from_orm(r) for r in results],
        message="Validation completed"
    )


@router.get("/entries/{entry_id}/validation-results", response_model=dict)
@require_permissions(["entries:read"])
async def get_validation_results(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get validation results for an entry"""
    results = validation_service.get_validation_results(db, entry_id, current_user.tenant_id)
    return success_response(data=[ValidationResultResponse.from_orm(r) for r in results])
