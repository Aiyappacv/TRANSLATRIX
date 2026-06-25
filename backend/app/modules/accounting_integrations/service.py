"""
Accounting Integrations Service
Business logic for accounting software integrations
"""
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
import structlog

from app.modules.accounting_integrations.registry import ConnectorRegistry
from app.modules.entries.models import FinancialEntry
from app.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger(__name__)


class AccountingIntegrationsService:
    """Service for managing accounting software integrations"""

    @staticmethod
    def list_available_connectors() -> List[Dict[str, Any]]:
        """List all available connectors"""
        return ConnectorRegistry.list_connectors()

    @staticmethod
    def test_connector(
        connector_id: str,
        config: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Test connector connection

        Args:
            connector_id: Connector identifier
            config: Connector configuration

        Returns:
            Tuple of (is_connected, error_message)
        """
        try:
            connector = ConnectorRegistry.get_connector(connector_id, config)
            is_connected, error_message = connector.test_connection()

            logger.info(
                "connector_test_completed",
                connector=connector_id,
                connected=is_connected
            )

            return is_connected, error_message

        except Exception as e:
            logger.error("connector_test_failed", connector=connector_id, error=str(e))
            return False, str(e)

    @staticmethod
    def post_entry(
        db: Session,
        tenant_id: UUID,
        entry_id: UUID,
        connector_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post financial entry to accounting software

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_id: Entry ID
            connector_id: Connector identifier
            config: Connector configuration

        Returns:
            Posting result
        """
        # Get financial entry
        entry = db.query(FinancialEntry).filter(
            and_(
                FinancialEntry.id == entry_id,
                FinancialEntry.tenant_id == tenant_id
            )
        ).first()

        if not entry:
            raise NotFoundError(f"Financial entry {entry_id} not found")

        # Get connector
        try:
            connector = ConnectorRegistry.get_connector(connector_id, config)
        except ValueError as e:
            raise ValidationError(str(e))

        # Build entry data
        entry_data = AccountingIntegrationsService._build_entry_data(entry)

        # Validate
        is_valid, error_message = connector.validate_entry(entry_data)
        if not is_valid:
            raise ValidationError(f"Entry validation failed: {error_message}")

        # Post to connector
        try:
            result = connector.post_journal_entry(entry_data)

            logger.info(
                "entry_posted_successfully",
                connector=connector_id,
                entry_id=str(entry_id),
                document_number=result.get("document_number")
            )

            return result

        except Exception as e:
            logger.error(
                "entry_posting_failed",
                connector=connector_id,
                entry_id=str(entry_id),
                error=str(e)
            )
            raise ValidationError(f"Posting failed: {str(e)}")

    @staticmethod
    def _build_entry_data(entry: FinancialEntry) -> Dict[str, Any]:
        """Build entry data for connector"""
        # Extract data from FinancialEntry
        return {
            "header": {
                "document_date": entry.created_at,
                "posting_date": entry.created_at,
                "document_type": entry.document_type or "Journal Entry",
                "reference_id": str(entry.id),
                "header_text": f"Entry from TRANSLATRIX - {entry.id}",
                "currency": "USD"
            },
            "line_items": entry.extracted_data.get("line_items", [])
        }
