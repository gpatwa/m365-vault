"""Connector registry — manages available SaaS platform connectors.

Adding a new platform:
1. Create new_platform_connector.py extending BaseConnector
2. Register here: CONNECTORS["new_platform"] = NewPlatformConnector
"""
from app.connectors.base_connector import BaseConnector, ConnectorInfo
from app.connectors.m365_connector import M365Connector

# ── Registry ──
# Add new connectors here as they're implemented
CONNECTORS: dict[str, BaseConnector] = {
    "microsoft365": M365Connector(),
}

# Coming soon placeholders (shown in UI but not functional)
COMING_SOON: list[ConnectorInfo] = [
    ConnectorInfo(
        platform_key="google_workspace",
        display_name="Google Workspace",
        description="Gmail, Drive, Calendar, Chat, Admin",
        icon="google",
        available=False,
        auth_type="oauth2",
    ),
    ConnectorInfo(
        platform_key="salesforce",
        display_name="Salesforce",
        description="Accounts, Contacts, Opportunities, Cases",
        icon="salesforce",
        available=False,
        auth_type="oauth2",
    ),
    ConnectorInfo(
        platform_key="slack",
        display_name="Slack",
        description="Channels, Messages, Files, Users",
        icon="slack",
        available=False,
        auth_type="oauth2",
    ),
]


def get_connector(platform_key: str) -> BaseConnector:
    """Get a connector by platform key."""
    connector = CONNECTORS.get(platform_key)
    if not connector:
        raise ValueError(f"Unknown platform: {platform_key}. Available: {list(CONNECTORS.keys())}")
    return connector


def list_connectors() -> list[ConnectorInfo]:
    """List all available and coming-soon connectors."""
    available = [c.info() for c in CONNECTORS.values()]
    return available + COMING_SOON
