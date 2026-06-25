"""Entries Routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.database import get_db
from app.dependencies import get_current_user, require_permission, require_permissions
from app.core.response import success_response
from app.modules.entries.service import EntriesService
from app.modules.entries.schemas import FinancialEntryResponse
from app.modules.users.models import User

router = APIRouter()
entries_service = EntriesService()


@router.get("/", response_model=dict)
@require_permissions(["entries:read"])
async def list_entries(
    file_id: UUID = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List financial entries"""
    entries = entries_service.get_entries(db, current_user.tenant_id, file_id)
    return success_response(data=[FinancialEntryResponse.from_orm(e) for e in entries])
