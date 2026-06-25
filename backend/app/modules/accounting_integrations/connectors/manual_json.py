"""
Manual JSON Export Connector
Exports entries as JSON for manual import
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import structlog

from app.modules.accounting_integrations.connectors.base import (
    BaseAccountingConnector,
    ConnectorCapability
)

logger = structlog.get_logger(__name__)


class ManualJSONConnector(BaseAccountingConnector):
    """Manual JSON export connector for offline processing"""

    def get_name(self) -> str:
        return "Manual JSON Export"

    def get_capabilities(self) -> List[ConnectorCapability]:
        return [
            ConnectorCapability.JOURNAL_ENTRIES,
            ConnectorCapability.SUPPLIER_INVOICES,
            ConnectorCapability.CUSTOMER_INVOICES,
            ConnectorCapability.BANK_TRANSACTIONS,
            ConnectorCapability.EXPENSE_REPORTS
        ]

    def test_connection(self) -> tuple[bool, Optional[str]]:
        """Test connection - Always successful for manual export"""
        logger.info("testing_manual_json_connector")
        return True, None

    def authenticate(self) -> tuple[bool, Optional[str]]:
        """Authenticate - Not required for manual export"""
        return True, None

    def post_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Export journal entry as JSON

        Args:
            entry_data: Journal entry data

        Returns:
            Response with JSON export
        """
        logger.info("exporting_to_json", entry_type="journal_entry")

        # Format entry data for export
        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "connector": "manual_json",
            "entry_type": "journal_entry",
            "data": entry_data,
            "formatted_entry": self._format_journal_entry(entry_data)
        }

        # Convert to pretty JSON string
        json_export = json.dumps(export_data, indent=2, default=str)

        return {
            "connector": "manual_json",
            "document_number": f"JSON-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "status": "exported",
            "export_format": "json",
            "json_data": json_export,
            "download_ready": True
        }

    def _format_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format journal entry for manual import"""
        header = entry_data.get("header", {})
        line_items = entry_data.get("line_items", [])

        formatted = {
            "header": {
                "document_date": header.get("document_date"),
                "posting_date": header.get("posting_date"),
                "document_type": header.get("document_type", "Journal Entry"),
                "reference": header.get("reference_id"),
                "description": header.get("header_text"),
                "currency": header.get("currency", "USD")
            },
            "line_items": []
        }

        total_debit = 0
        total_credit = 0

        for item in line_items:
            amount = float(item.get("amount", 0))
            is_debit = amount >= 0

            if is_debit:
                total_debit += abs(amount)
            else:
                total_credit += abs(amount)

            formatted_item = {
                "account": item.get("gl_account"),
                "description": item.get("item_text"),
                "debit": abs(amount) if is_debit else 0,
                "credit": abs(amount) if not is_debit else 0,
                "cost_center": item.get("cost_center"),
                "department": item.get("department"),
                "project": item.get("project")
            }
            formatted["line_items"].append(formatted_item)

        formatted["totals"] = {
            "total_debit": total_debit,
            "total_credit": total_credit,
            "balanced": abs(total_debit - total_credit) < 0.01
        }

        return formatted
