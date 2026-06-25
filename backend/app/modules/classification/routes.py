"""Classification Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.classification.service import ClassificationService
from app.modules.classification.schemas import ClassificationResponse
from app.modules.users.models import User

router = APIRouter()
classification_service = ClassificationService()


@router.post("/entries/{entry_id}/classify", response_model=dict)
@require_permissions(["entries:write"])
async def classify_entry(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Classify a financial entry"""
    classification = await classification_service.classify_entry(db, entry_id)
    return success_response(data=ClassificationResponse.from_orm(classification))
