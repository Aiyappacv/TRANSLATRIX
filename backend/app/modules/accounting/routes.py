"""Accounting Routes"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.accounting.service import AccountingService
from app.modules.accounting.schemas import AccountingEntryResponse
from app.modules.users.models import User

router = APIRouter()
accounting_service = AccountingService()


@router.post("/entries/{entry_id}/generate", response_model=dict)
@require_permissions(["entries:write"])
async def generate_accounting_entries(
    entry_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate accounting entries for financial entry"""
    entries = accounting_service.generate_entries(db, entry_id, current_user.tenant_id)
    return success_response(data=[AccountingEntryResponse.from_orm(e) for e in entries])
