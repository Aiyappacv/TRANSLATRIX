"""
Base SAP Adapter
Abstract interface for SAP posting adapters
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from uuid import UUID


class BaseSAPAdapter(ABC):
    """Base adapter interface for SAP integrations"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize adapter with configuration

        Args:
            config: SAP connection configuration
        """
        self.config = config
        self.base_url = config.get("base_url")
        self.client = config.get("client")
        self.username = config.get("username")
        self.password = config.get("password")

    @abstractmethod
    def build_payload(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build SAP posting payload from entry data

        Args:
            entry_data: Financial entry data

        Returns:
            SAP-formatted payload
        """
        pass

    @abstractmethod
    def validate_payload(self, payload: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate SAP payload before posting

        Args:
            payload: SAP payload to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass

    @abstractmethod
    def post_to_sap(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post payload to SAP

        Args:
            payload: SAP-formatted payload

        Returns:
            SAP response
        """
        pass

    @abstractmethod
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse SAP response

        Args:
            response: Raw SAP response

        Returns:
            Parsed response with document number, status, etc.
        """
        pass

    def get_api_endpoint(self) -> str:
        """Get the API endpoint for this adapter"""
        return f"{self.base_url}/sap/opu/odata/sap"
