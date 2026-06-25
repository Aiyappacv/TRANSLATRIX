"""
Connector Registry
Central registry for all accounting software connectors
"""
from typing import Dict, Type, List, Optional
import structlog

from app.modules.accounting_integrations.connectors.base import BaseAccountingConnector
from app.modules.accounting_integrations.connectors.quickbooks import QuickBooksConnector
from app.modules.accounting_integrations.connectors.xero import XeroConnector
from app.modules.accounting_integrations.connectors.zoho_books import ZohoBooksConnector
from app.modules.accounting_integrations.connectors.tally_prime import TallyPrimeConnector
from app.modules.accounting_integrations.connectors.sage import SageConnector
from app.modules.accounting_integrations.connectors.netsuite import NetSuiteConnector
from app.modules.accounting_integrations.connectors.manual_json import ManualJSONConnector
from app.modules.accounting_integrations.connectors.webhook import WebhookConnector

logger = structlog.get_logger(__name__)


class ConnectorRegistry:
    """Registry for all accounting software connectors"""

    _connectors: Dict[str, Type[BaseAccountingConnector]] = {
        "quickbooks": QuickBooksConnector,
        "xero": XeroConnector,
        "zoho_books": ZohoBooksConnector,
        "tally_prime": TallyPrimeConnector,
        "sage": SageConnector,
        "netsuite": NetSuiteConnector,
        "manual_json": ManualJSONConnector,
        "webhook": WebhookConnector,
    }

    @classmethod
    def get_connector(
        cls,
        connector_name: str,
        config: Dict[str, any]
    ) -> BaseAccountingConnector:
        """
        Get connector instance by name

        Args:
            connector_name: Connector identifier
            config: Connector configuration

        Returns:
            Initialized connector instance

        Raises:
            ValueError: If connector not found
        """
        connector_class = cls._connectors.get(connector_name.lower())

        if not connector_class:
            raise ValueError(f"Connector '{connector_name}' not found")

        logger.info("initializing_connector", connector=connector_name)
        return connector_class(config)

    @classmethod
    def list_connectors(cls) -> List[Dict[str, any]]:
        """
        List all available connectors

        Returns:
            List of connector information
        """
        connectors = []

        for name, connector_class in cls._connectors.items():
            # Create temp instance to get info
            temp_instance = connector_class({})

            connectors.append({
                "id": name,
                "name": temp_instance.get_name(),
                "capabilities": [cap.value for cap in temp_instance.get_capabilities()],
                "status": "active" if name in ["manual_json", "webhook"] else "placeholder"
            })

        return connectors

    @classmethod
    def register_connector(
        cls,
        name: str,
        connector_class: Type[BaseAccountingConnector]
    ) -> None:
        """
        Register a new connector

        Args:
            name: Connector identifier
            connector_class: Connector class
        """
        if name in cls._connectors:
            logger.warning("connector_already_registered", connector=name)

        cls._connectors[name] = connector_class
        logger.info("connector_registered", connector=name)

    @classmethod
    def is_connector_available(cls, connector_name: str) -> bool:
        """Check if connector is available"""
        return connector_name.lower() in cls._connectors
