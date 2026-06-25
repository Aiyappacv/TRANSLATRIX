"""
Base Accounting Connector
Abstract interface for accounting software integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum


class ConnectorCapability(Enum):
    """Connector capabilities"""
    JOURNAL_ENTRIES = "journal_entries"
    SUPPLIER_INVOICES = "supplier_invoices"
    CUSTOMER_INVOICES = "customer_invoices"
    BANK_TRANSACTIONS = "bank_transactions"
    EXPENSE_REPORTS = "expense_reports"


class BaseAccountingConnector(ABC):
    """Base connector interface for accounting software integrations"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration

        Args:
            config: Connector-specific configuration
        """
        self.config = config
        self.name = self.__class__.__name__
        self.capabilities = self.get_capabilities()

    @abstractmethod
    def get_name(self) -> str:
        """Get connector name"""
        pass

    @abstractmethod
    def get_capabilities(self) -> List[ConnectorCapability]:
        """Get list of supported capabilities"""
        pass

    @abstractmethod
    def test_connection(self) -> tuple[bool, Optional[str]]:
        """
        Test connection to accounting software

        Returns:
            Tuple of (is_connected, error_message)
        """
        pass

    @abstractmethod
    def authenticate(self) -> tuple[bool, Optional[str]]:
        """
        Authenticate with accounting software

        Returns:
            Tuple of (is_authenticated, error_message)
        """
        pass

    @abstractmethod
    def post_journal_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post journal entry

        Args:
            entry_data: Journal entry data

        Returns:
            Response with document number and status
        """
        pass

    def post_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post invoice (optional)

        Args:
            invoice_data: Invoice data

        Returns:
            Response with document number and status
        """
        raise NotImplementedError(f"{self.name} does not support invoice posting")

    def get_chart_of_accounts(self) -> List[Dict[str, Any]]:
        """
        Get chart of accounts (optional)

        Returns:
            List of GL accounts
        """
        raise NotImplementedError(f"{self.name} does not support chart of accounts retrieval")

    def validate_entry(self, entry_data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate entry data before posting

        Args:
            entry_data: Entry data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Default validation
        if not entry_data:
            return False, "Entry data is empty"

        return True, None
