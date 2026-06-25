"""
Accounting Integrations Routes
API endpoints for accounting software integrations
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.database import get_db
from app.dependencies import get_current_user, get_tenant_context
from app.modules.accounting_integrations.service import AccountingIntegrationsService
from app.modules.accounting_integrations.schemas import (
    ConnectorListResponse,
    ConnectorInfo,
    ConnectorTestRequest,
    ConnectorTestResponse,
    PostingRequest,
    PostingResponse
)

router = APIRouter()


@router.get("", response_model=ConnectorListResponse)
def list_accounting_integrations(
    current_user: dict = Depends(get_current_user)
):
    """List all available accounting software integrations"""
    connectors = AccountingIntegrationsService.list_available_connectors()

    return ConnectorListResponse(
        connectors=[ConnectorInfo(**c) for c in connectors],
        total=len(connectors)
    )


@router.post("/{connector_id}/test", response_model=ConnectorTestResponse)
def test_connector(
    connector_id: str,
    request: ConnectorTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """Test accounting software connector"""
    config = request.config or {}

    is_connected, error_message = AccountingIntegrationsService.test_connector(
        connector_id=connector_id,
        config=config
    )

    return ConnectorTestResponse(
        connector_id=connector_id,
        connected=is_connected,
        message=error_message
    )


@router.post("/{connector_id}/post/{entry_id}", response_model=PostingResponse)
def post_entry_to_connector(
    connector_id: str,
    entry_id: UUID,
    request: PostingRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    tenant_context: dict = Depends(get_tenant_context)
):
    """Post financial entry to accounting software"""
    config = request.config or {}

    result = AccountingIntegrationsService.post_entry(
        db=db,
        tenant_id=tenant_context["tenant_id"],
        entry_id=entry_id,
        connector_id=connector_id,
        config=config
    )

    return PostingResponse(
        connector_id=connector_id,
        entry_id=str(entry_id),
        document_number=result.get("document_number"),
        status=result.get("status", "posted"),
        response_data=result
    )
