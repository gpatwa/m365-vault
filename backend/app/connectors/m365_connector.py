"""Microsoft 365 connector — OAuth admin consent flow.

Uses the multi-tenant KavachIQ Connector app registered in Azure AD.
Customer clicks "Connect Microsoft 365" → redirects to Microsoft admin
consent → accepts permissions → redirected back with tenant_id.

No client secrets stored per customer — KavachIQ uses its own app
credentials with consented access to customer's tenant.
"""
import logging

import httpx
import msal

from app.config import settings
from app.connectors.base_connector import (
    BaseConnector, ConnectorInfo, ConnectionResult, DiscoveryResult,
)

logger = logging.getLogger(__name__)

# Microsoft Graph resource ID
MS_GRAPH = "https://graph.microsoft.com"

# Required application permissions
M365_PERMISSIONS = [
    {"name": "Directory.Read.All", "description": "Read directory data (users, groups, roles)", "category": "backup"},
    {"name": "User.Read.All", "description": "Read all user profiles", "category": "backup"},
    {"name": "Mail.Read", "description": "Read user mailboxes", "category": "backup"},
    {"name": "Calendars.Read", "description": "Read user calendars", "category": "backup"},
    {"name": "Contacts.Read", "description": "Read user contacts", "category": "backup"},
    {"name": "Files.Read.All", "description": "Read all files (OneDrive)", "category": "backup"},
    {"name": "Sites.Read.All", "description": "Read SharePoint sites", "category": "backup"},
    {"name": "Chat.Read.All", "description": "Read Teams chats", "category": "backup"},
    {"name": "ChannelMessage.Read.All", "description": "Read Teams channel messages", "category": "backup"},
    {"name": "Team.ReadBasic.All", "description": "Read Teams info", "category": "backup"},
    {"name": "TeamSettings.Read.All", "description": "Read Teams settings", "category": "backup"},
    {"name": "Group.Read.All", "description": "Read all groups", "category": "backup"},
    {"name": "Application.ReadWrite.All", "description": "Manage app registrations", "category": "setup"},
]


class M365Connector(BaseConnector):
    """Microsoft 365 connector using multi-tenant admin consent."""

    def __init__(self):
        self.app_id = settings.CONNECTOR_APP_ID
        self.app_secret = settings.CONNECTOR_APP_SECRET

    def info(self) -> ConnectorInfo:
        return ConnectorInfo(
            platform_key="microsoft365",
            display_name="Microsoft 365",
            description="Exchange, OneDrive, SharePoint, Teams, Entra ID",
            icon="microsoft365",
            available=bool(self.app_id),
            auth_type="admin_consent",
            required_permissions=[p["name"] for p in M365_PERMISSIONS],
        )

    def get_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate Microsoft admin consent URL.

        Uses /common/adminconsent for multi-tenant consent.
        Customer's Global Admin signs in and approves permissions.
        """
        if not self.app_id:
            raise ValueError("CONNECTOR_APP_ID not configured")

        url = (
            f"https://login.microsoftonline.com/common/adminconsent"
            f"?client_id={self.app_id}"
            f"&redirect_uri={redirect_uri}"
        )
        if state:
            url += f"&state={state}"
        return url

    async def handle_callback(
        self, code: str = None, state: str = None,
        admin_consent: bool = False, tenant: str = None,
        **kwargs,
    ) -> ConnectionResult:
        """Handle Microsoft admin consent callback.

        Microsoft redirects back with:
        - admin_consent=True (consent granted)
        - tenant=<customer-tenant-id>

        We then use our app credentials to get a token for the customer's tenant.
        """
        if not admin_consent or not tenant:
            return ConnectionResult(
                success=False,
                error="Admin consent was not granted or tenant ID missing",
            )

        # Retry token acquisition — Azure AD can take seconds to propagate consent
        import asyncio
        max_retries = 3
        last_error = ""

        for attempt in range(max_retries):
            try:
                msal_app = msal.ConfidentialClientApplication(
                    client_id=self.app_id,
                    client_credential=self.app_secret,
                    authority=f"https://login.microsoftonline.com/{tenant}",
                )
                token_result = msal_app.acquire_token_for_client(
                    scopes=[f"{MS_GRAPH}/.default"]
                )

                if "error" in token_result:
                    last_error = token_result.get('error_description', token_result.get('error', 'Unknown'))
                    error_code = token_result.get('error', '')

                    # AADSTS7000215 = invalid client secret — don't retry, it won't help
                    if 'AADSTS7000215' in last_error:
                        logger.error(f"Invalid client secret for KavachIQ Connector app. Check CONNECTOR_APP_SECRET env var.")
                        return ConnectionResult(
                            success=False,
                            error="KavachIQ configuration error: the connector app secret is invalid. Please contact support.",
                        )

                    # AADSTS700016 = app not found in tenant — consent may not have propagated
                    if 'AADSTS700016' in last_error or 'AADSTS65001' in last_error:
                        if attempt < max_retries - 1:
                            wait = (attempt + 1) * 5  # 5s, 10s
                            logger.info(f"Consent not yet propagated for tenant {tenant}. Retry {attempt+1}/{max_retries} in {wait}s...")
                            await asyncio.sleep(wait)
                            continue

                    # Other token errors — retry once
                    if attempt < max_retries - 1:
                        await asyncio.sleep(3)
                        continue

                    return ConnectionResult(
                        success=False,
                        error=self._friendly_error(last_error),
                    )

                # Success — get tenant name
                tenant_name = await self._get_tenant_name(
                    token_result["access_token"], tenant
                )

                return ConnectionResult(
                    success=True,
                    tenant_id=tenant,
                    tenant_name=tenant_name or f"Tenant {tenant[:8]}",
                    credentials={
                        "ms_tenant_id": tenant,
                        "client_id": self.app_id,
                        "client_secret": self.app_secret,
                        "auth_method": "multi_tenant_app",
                    },
                )

            except Exception as e:
                last_error = str(e)
                logger.error(f"M365 callback attempt {attempt+1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(3)
                    continue

        return ConnectionResult(success=False, error=self._friendly_error(last_error))

    @staticmethod
    def _friendly_error(technical_error: str) -> str:
        """Convert AADSTS codes to user-friendly messages."""
        if 'AADSTS7000215' in technical_error:
            return "KavachIQ configuration error. The connector credentials need to be updated. Please contact support."
        if 'AADSTS700016' in technical_error:
            return "Microsoft hasn't finished processing your consent yet. Please wait a minute and try again."
        if 'AADSTS65001' in technical_error:
            return "Admin consent is required. Please ask a Global Administrator to approve the connection."
        if 'AADSTS50011' in technical_error:
            return "Redirect URL mismatch. Please contact support."
        if 'AADSTS90002' in technical_error:
            return "Could not find your Microsoft 365 tenant. Please check your organization's Azure AD configuration."
        return f"Connection failed: {technical_error[:200]}"

    async def test_connection(self, credentials: dict) -> bool:
        """Test M365 connection by calling Graph API."""
        try:
            tenant_id = credentials["ms_tenant_id"]
            msal_app = msal.ConfidentialClientApplication(
                client_id=credentials["client_id"],
                client_credential=credentials["client_secret"],
                authority=f"https://login.microsoftonline.com/{tenant_id}",
            )
            token = msal_app.acquire_token_for_client(
                scopes=[f"{MS_GRAPH}/.default"]
            )
            if "error" in token:
                return False

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{MS_GRAPH}/v1.0/organization",
                    headers={"Authorization": f"Bearer {token['access_token']}"},
                )
                return resp.status_code == 200

        except Exception:
            return False

    async def discover(self, credentials: dict) -> DiscoveryResult:
        """Discover M365 workloads (users, mailboxes, sites, teams, etc.)."""
        try:
            tenant_id = credentials["ms_tenant_id"]
            msal_app = msal.ConfidentialClientApplication(
                client_id=credentials["client_id"],
                client_credential=credentials["client_secret"],
                authority=f"https://login.microsoftonline.com/{tenant_id}",
            )
            token = msal_app.acquire_token_for_client(
                scopes=[f"{MS_GRAPH}/.default"]
            )
            if "error" in token:
                return DiscoveryResult(success=False, error="Token acquisition failed")

            access_token = token["access_token"]
            workloads = {}

            async with httpx.AsyncClient(timeout=30) as client:
                headers = {"Authorization": f"Bearer {access_token}"}

                # Count users (Exchange + OneDrive)
                users_resp = await client.get(
                    f"{MS_GRAPH}/v1.0/users?$select=id&$top=999",
                    headers=headers,
                )
                if users_resp.status_code == 200:
                    users = users_resp.json().get("value", [])
                    workloads["exchange"] = len(users)
                    workloads["onedrive"] = len(users)

                # Count SharePoint sites
                sites_resp = await client.get(
                    f"{MS_GRAPH}/v1.0/sites/getAllSites?$select=id&$top=999",
                    headers=headers,
                )
                if sites_resp.status_code == 200:
                    sites = sites_resp.json().get("value", [])
                    workloads["sharepoint"] = len(sites)

                # Count Teams
                teams_resp = await client.get(
                    f"{MS_GRAPH}/v1.0/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')&$select=id&$top=999",
                    headers={**headers, "ConsistencyLevel": "eventual"},
                )
                if teams_resp.status_code == 200:
                    teams = teams_resp.json().get("value", [])
                    workloads["teams"] = len(teams)

                # Entra ID is always 1 (the directory itself)
                workloads["entra_id"] = 1

            total = sum(workloads.values())
            return DiscoveryResult(
                success=True,
                workloads=workloads,
                total_objects=total,
            )

        except Exception as e:
            logger.error(f"M365 discovery failed: {e}")
            return DiscoveryResult(success=False, error=str(e))

    def get_required_permissions(self) -> list[dict]:
        return M365_PERMISSIONS

    # ── Private Helpers ──

    async def _get_tenant_name(self, access_token: str, tenant_id: str) -> str:
        """Get tenant display name from Graph API."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{MS_GRAPH}/v1.0/organization",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                if resp.status_code == 200:
                    orgs = resp.json().get("value", [])
                    if orgs:
                        return orgs[0].get("displayName", "")
        except Exception:
            pass
        return ""
