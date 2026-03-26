"""Base connector interface for all SaaS platform integrations.

Every SaaS platform (M365, Google Workspace, Salesforce, Slack) implements
this interface. The onboarding flow is platform-agnostic — only the OAuth
URLs and API calls differ.

Flow:
1. get_auth_url() → redirect customer to platform's OAuth consent
2. handle_callback() → exchange code for credentials
3. test_connection() → verify access works
4. discover() → find protectable objects (mailboxes, drives, sites, etc.)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ConnectorInfo:
    """Platform metadata shown in the UI."""
    platform_key: str           # "microsoft365", "google_workspace", etc.
    display_name: str           # "Microsoft 365"
    description: str            # "Exchange, OneDrive, SharePoint, Teams, Entra ID"
    icon: str                   # Icon identifier for frontend
    available: bool             # True if implemented, False for "Coming Soon"
    auth_type: str              # "admin_consent", "oauth2", "service_account"
    required_permissions: list[str] = field(default_factory=list)


@dataclass
class ConnectionResult:
    """Result of OAuth callback / connection attempt."""
    success: bool
    tenant_id: str = None       # Platform tenant/org identifier
    tenant_name: str = None     # Human-readable name
    credentials: dict = None    # Encrypted credentials to store
    error: str = None


@dataclass
class DiscoveryResult:
    """Result of workload discovery."""
    success: bool
    workloads: dict = None      # {workload_type: count}
    total_objects: int = 0
    error: str = None


class BaseConnector(ABC):
    """Abstract base for all SaaS platform connectors.

    To add a new platform:
    1. Create NewPlatformConnector(BaseConnector)
    2. Implement all abstract methods
    3. Register in registry.py
    """

    @abstractmethod
    def info(self) -> ConnectorInfo:
        """Return platform metadata for UI display."""
        ...

    @abstractmethod
    def get_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate OAuth authorization URL for customer to consent.

        Args:
            redirect_uri: Where to redirect after consent
            state: CSRF protection token

        Returns:
            Full authorization URL to redirect the customer to
        """
        ...

    @abstractmethod
    async def handle_callback(
        self, code: str = None, state: str = None,
        admin_consent: bool = False, tenant: str = None,
        **kwargs,
    ) -> ConnectionResult:
        """Handle OAuth callback after customer consents.

        For M365: admin consent returns tenant_id directly
        For Google/Salesforce: exchange authorization code for tokens

        Returns:
            ConnectionResult with credentials to store
        """
        ...

    @abstractmethod
    async def test_connection(self, credentials: dict) -> bool:
        """Test that stored credentials still work.

        Args:
            credentials: Previously stored credentials from handle_callback

        Returns:
            True if connection is healthy
        """
        ...

    @abstractmethod
    async def discover(self, credentials: dict) -> DiscoveryResult:
        """Discover protectable objects in the customer's platform.

        Args:
            credentials: Stored credentials

        Returns:
            DiscoveryResult with workload counts
        """
        ...

    @abstractmethod
    def get_required_permissions(self) -> list[dict]:
        """Return list of required permissions with descriptions.

        Returns:
            [{"name": "Mail.Read", "description": "Read user mailboxes", "category": "backup"}]
        """
        ...
