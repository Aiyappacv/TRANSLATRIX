"""
Journal Entry Adapter (FB50)
SAP journal entry posting adapter
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog

from app.modules.sap.adapters.base import BaseSAPAdapter

logger = structlog.get_logger(__name__)


class JournalEntryAdapter(BaseSAPAdapter):
    """Adapter for posting journal entries to SAP (FB50 - T-Code)"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_service = "API_JOURNALENTRY_SRV"

    def build_payload(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build SAP journal entry payload

        Args:
            entry_data: Financial entry data with line items

        Returns:
            SAP-formatted journal entry payload
        """
        header_data = entry_data.get("header", {})
        line_items = entry_data.get("line_items", [])

        payload = {
            "CompanyCode": header_data.get("company_code", ""),
            "DocumentDate": self._format_date(header_data.get("document_date")),
            "PostingDate": self._format_date(header_data.get("posting_date")),
            "DocumentType": header_data.get("document_type", "SA"),
            "DocumentHeaderText": header_data.get("header_text", ""),
            "DocumentReferenceID": header_data.get("reference_id", ""),
            "BusinessTransactionType": header_data.get("business_transaction_type", ""),
            "to_JournalEntryItem": []
        }

        # Build line items
        for idx, item in enumerate(line_items, start=1):
            line_item = {
                "ReferenceDocumentItem": str(idx).zfill(6),
                "GLAccount": item.get("gl_account", ""),
                "AmountInTransactionCurrency": {
                    "Amount": str(abs(item.get("amount", 0))),
                    "Currency": item.get("currency", "USD")
                },
                "DebitCreditCode": "S" if item.get("amount", 0) >= 0 else "H",
                "DocumentItemText": item.get("item_text", ""),
                "CostCenter": item.get("cost_center", ""),
                "ProfitCenter": item.get("profit_center", ""),
                "TaxCode": item.get("tax_code", ""),
                "ValueDate": self._format_date(item.get("value_date"))
            }
            payload["to_JournalEntryItem"].append(line_item)

        return payload

    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate journal entry payload

        Args:
            payload: Journal entry payload

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Required fields
        if not payload.get("CompanyCode"):
            return False, "Company code is required"

        if not payload.get("DocumentDate"):
            return False, "Document date is required"

        if not payload.get("PostingDate"):
            return False, "Posting date is required"

        line_items = payload.get("to_JournalEntryItem", [])
        if not line_items:
            return False, "At least one line item is required"

        # Validate line items
        total_debit = 0
        total_credit = 0

        for item in line_items:
            if not item.get("GLAccount"):
                return False, "GL Account is required for all line items"

            amount_data = item.get("AmountInTransactionCurrency", {})
            if not amount_data.get("Amount"):
                return False, "Amount is required for all line items"

            amount = float(amount_data.get("Amount", 0))
            debit_credit = item.get("DebitCreditCode", "")

            if debit_credit == "S":
                total_debit += amount
            elif debit_credit == "H":
                total_credit += amount

        # Check balance
        if abs(total_debit - total_credit) > 0.01:
            return False, f"Journal entry not balanced: Debit={total_debit}, Credit={total_credit}"

        return True, None

    def post_to_sap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post journal entry to SAP

        Args:
            payload: Journal entry payload

        Returns:
            SAP response
        """
        # This is a placeholder - actual implementation would use requests library
        # to call SAP OData API with OAuth authentication

        logger.info(
            "posting_journal_entry_to_sap",
            company_code=payload.get("CompanyCode"),
            line_items=len(payload.get("to_JournalEntryItem", []))
        )

        # Simulated response for now
        # In production, this would be:
        # response = requests.post(
        #     f"{self.get_api_endpoint()}/{self.api_service}/A_JournalEntry",
        #     json=payload,
        #     auth=(self.username, self.password),
        #     headers={"Content-Type": "application/json"}
        # )
        # return response.json()

        return {
            "d": {
                "AccountingDocument": f"SAP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "FiscalYear": datetime.now().year,
                "CompanyCode": payload.get("CompanyCode"),
                "PostingDate": payload.get("PostingDate"),
                "AccountingDocumentType": payload.get("DocumentType")
            }
        }

    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse SAP journal entry response

        Args:
            response: Raw SAP response

        Returns:
            Parsed response
        """
        data = response.get("d", {})

        return {
            "document_number": data.get("AccountingDocument"),
            "fiscal_year": data.get("FiscalYear"),
            "company_code": data.get("CompanyCode"),
            "posting_date": data.get("PostingDate"),
            "document_type": data.get("AccountingDocumentType"),
            "status": "posted",
            "raw_response": response
        }

    def _format_date(self, date_value: Any) -> str:
        """Format date for SAP (YYYY-MM-DD)"""
        if not date_value:
            return datetime.now().strftime("%Y-%m-%d")

        if isinstance(date_value, str):
            return date_value

        if isinstance(date_value, datetime):
            return date_value.strftime("%Y-%m-%d")

        return str(date_value)
