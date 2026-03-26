"""SaaS platform connectors for multi-platform onboarding."""
from app.connectors.base_connector import BaseConnector
from app.connectors.m365_connector import M365Connector
from app.connectors.registry import get_connector, list_connectors

__all__ = ["BaseConnector", "M365Connector", "get_connector", "list_connectors"]
