"""SAP Mapping Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.sap_mapping.service import SAPMappingService
from app.modules.users.models import User

router = APIRouter()
sap_service = SAPMappingService()


@router.get("/suggest/{entry_id}", response_model=dict)
@require_permissions(["entries:read"])
async def suggest_sap_mapping(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Suggest SAP mapping for entry"""
    # Implementation placeholder
    return success_response(data={"tcode": "FB01", "gl_accounts": []})
