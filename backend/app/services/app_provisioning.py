"""App Registration Provisioning Service.

Automates the creation of Azure AD app registrations for M365 Vault tenants.

Flow:
1. Admin signs in with Microsoft (delegated flow, needs Application.ReadWrite.All)
2. We create an app registration in their tenant with all required Graph API permissions
3. We create a client secret for the app
4. We trigger admin consent for the app permissions
5. Store the credentials — admin never copies/pastes anything

Required delegated permissions for the provisioning app:
- Application.ReadWrite.All (to create app registrations)
- DelegatedPermissionGrant.ReadWrite.All (optional, for consent)
"""
import logging
import uuid
from datetime import datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Microsoft Graph resource app ID (constant)
MS_GRAPH_RESOURCE_APP_ID = "00000003-0000-0000-c000-000000000000"

# Required application permissions for M365 Vault backup/restore
REQUIRED_APP_PERMISSIONS = {
    # Backup (read-only)
    "Mail.Read": "810c84a8-4a9e-49e6-bf7d-12d183f40d01",
    "Calendars.Read": "798ee544-9d2d-430c-a058-570e29e34338",
    "Contacts.Read": "089fe4d0-434a-44c5-8827-41ba8a0b17f5",
    "Files.Read.All": "01d4f6ba-6a36-4f86-b5fa-0514e2aa4b40",
    "Sites.Read.All": "332a536c-c7ef-4017-ab91-336970924f0d",
    "User.Read.All": "df021288-bdef-4463-88db-98f22de89214",
    "Directory.Read.All": "7ab1d382-f21e-4acd-a863-ba3e13f7da61",
    "Chat.Read.All": "6b7d71aa-70aa-4810-a8d9-5d9fb2830017",
    "ChannelMessage.Read.All": "7b2449af-6ccd-4f4d-9f78-e550c10e2869",
    "Team.ReadBasic.All": "2280dda6-0bfd-44ee-a2f4-cb867cfc4c1e",
    "TeamSettings.Read.All": "242607bd-1d2c-432c-82eb-bdb27baa23ab",
    "Group.Read.All": "5b567255-7703-4780-807c-7be8301ae99b",
    # Restore (read-write)
    "Mail.ReadWrite": "e2a3a72e-5f79-4c64-b1b1-878b674786c9",
    "Calendars.ReadWrite": "ef54d2bf-783f-4e0f-bca1-3210c0444d99",
    "Contacts.ReadWrite": "6918b873-d688-4a76-8b30-e4baddca5513",
    "Files.ReadWrite.All": "75359482-378d-4052-8f01-80520e7db3cd",
    "Sites.ReadWrite.All": "9492366f-7969-46a4-8d15-ed1a20078fff",
    "User.ReadWrite.All": "741f803b-c850-494e-b5df-cde7c675a1ca",
    "Group.ReadWrite.All": "62a82d76-70ea-41e2-9197-370581804d09",
    "Application.ReadWrite.All": "1bfefb4e-e0b5-418b-a88f-73c46d2cc8e9",
    "Policy.ReadWrite.ConditionalAccess": "ad746e5c-0c53-4e22-8bab-3e3c4e8e4e7e",
    "RoleManagement.ReadWrite.Directory": "d01b97e9-cbc0-49fe-810a-e34c8e7e3c50",
}

# Minimum backup-only permissions
BACKUP_PERMISSIONS = {
    "Mail.Read", "Calendars.Read", "Contacts.Read",
    "Files.Read.All", "Sites.Read.All", "User.Read.All",
    "Directory.Read.All", "Chat.Read.All", "ChannelMessage.Read.All",
    "Team.ReadBasic.All", "TeamSettings.Read.All", "Group.Read.All",
}


class AppProvisioningService:
    """Automates Azure AD app registration for tenant onboarding."""

    def get_admin_consent_url(self, tenant_id: str, client_id: str, redirect_uri: str = None) -> str:
        """Generate the admin consent URL for an existing app registration.

        The admin clicks this link to grant all configured permissions at once.
        Omits redirect_uri if not registered in the app to avoid AADSTS500113.
        """
        url = (
            f"https://login.microsoftonline.com/{tenant_id}/adminconsent"
            f"?client_id={client_id}"
        )
        if redirect_uri:
            url += f"&redirect_uri={redirect_uri}"
        return url

    async def create_app_registration(
        self,
        access_token: str,
        app_name: str = "M365 Vault Backup",
    ) -> dict:
        """Create an app registration in the customer's tenant with all required permissions.

        Args:
            access_token: Delegated access token with Application.ReadWrite.All
            app_name: Display name for the app registration

        Returns:
            dict with appId, objectId, displayName
        """
        # Build required resource access list
        app_roles = []
        for perm_name, role_id in REQUIRED_APP_PERMISSIONS.items():
            if perm_name in BACKUP_PERMISSIONS:
                app_roles.append({
                    "id": role_id,
                    "type": "Role",  # Application permission
                })

        app_body = {
            "displayName": app_name,
            "signInAudience": "AzureADMyOrg",
            "requiredResourceAccess": [
                {
                    "resourceAppId": MS_GRAPH_RESOURCE_APP_ID,
                    "resourceAccess": app_roles,
                }
            ],
            "web": {
                "redirectUris": [settings.SSO_REDIRECT_URI] if settings.SSO_REDIRECT_URI else [],
            },
            "notes": f"Created by M365 Vault on {datetime.utcnow().isoformat()}",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://graph.microsoft.com/v1.0/applications",
                json=app_body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code not in (200, 201):
                error_data = response.json()
                raise ValueError(
                    f"Failed to create app registration: "
                    f"{error_data.get('error', {}).get('message', response.text)}"
                )

            app_data = response.json()
            logger.info(f"Created app registration: {app_data['displayName']} (appId={app_data['appId']})")

            return {
                "app_id": app_data["appId"],
                "object_id": app_data["id"],
                "display_name": app_data["displayName"],
            }

    async def create_client_secret(
        self,
        access_token: str,
        app_object_id: str,
        description: str = "M365 Vault Auto-Generated",
    ) -> dict:
        """Create a client secret for an app registration.

        Returns:
            dict with secretText (the actual secret value), keyId, endDateTime
        """
        body = {
            "passwordCredential": {
                "displayName": description,
                "endDateTime": "2026-12-31T23:59:59Z",  # 1 year validity
            }
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://graph.microsoft.com/v1.0/applications/{app_object_id}/addPassword",
                json=body,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code not in (200, 201):
                error_data = response.json()
                raise ValueError(
                    f"Failed to create client secret: "
                    f"{error_data.get('error', {}).get('message', response.text)}"
                )

            secret_data = response.json()
            logger.info(f"Created client secret for app {app_object_id}")

            return {
                "secret_text": secret_data["secretText"],
                "key_id": secret_data["keyId"],
                "end_date": secret_data.get("endDateTime"),
            }

    async def check_granted_permissions(
        self,
        access_token: str,
        app_id: str,
    ) -> dict:
        """Check which permissions have been granted (admin consented) for an app.

        Dynamically looks up role IDs from Microsoft Graph instead of using
        hardcoded IDs, ensuring accuracy across all tenants.

        Returns per-workload permission status.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            # Get MS Graph service principal to build role ID → name map
            ms_sp_response = await client.get(
                f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{MS_GRAPH_RESOURCE_APP_ID}'&$select=id,appRoles",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if ms_sp_response.status_code != 200 or not ms_sp_response.json().get("value"):
                return {"error": "Could not look up Microsoft Graph permissions"}

            ms_sp = ms_sp_response.json()["value"][0]
            role_id_to_name = {}
            for role in ms_sp.get("appRoles", []):
                if "Application" in (role.get("allowedMemberTypes") or []):
                    role_id_to_name[role["id"]] = role["value"]

            # Find our service principal by appId
            sp_response = await client.get(
                f"https://graph.microsoft.com/v1.0/servicePrincipals(appId='{app_id}')",
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if sp_response.status_code != 200:
                return {"error": "Service principal not found. Admin consent may not have been granted yet."}

            sp_data = sp_response.json()
            sp_id = sp_data["id"]

            # Get app role assignments (granted permissions) — paginate to get all
            all_assignments = []
            url = f"https://graph.microsoft.com/v1.0/servicePrincipals/{sp_id}/appRoleAssignments?$top=100"
            while url:
                assign_response = await client.get(
                    url, headers={"Authorization": f"Bearer {access_token}"},
                )
                if assign_response.status_code != 200:
                    return {"error": "Could not read permission assignments"}
                data = assign_response.json()
                all_assignments.extend(data.get("value", []))
                url = data.get("@odata.nextLink")

        # Map granted role IDs to permission names using the dynamic lookup
        granted_permissions = set()
        for assignment in all_assignments:
            perm_name = role_id_to_name.get(assignment["appRoleId"])
            if perm_name:
                granted_permissions.add(perm_name)

        # Build per-workload status
        workload_perms = {
            "exchange": {"backup": ["Mail.Read", "Calendars.Read", "Contacts.Read"], "restore": ["Mail.ReadWrite", "Calendars.ReadWrite", "Contacts.ReadWrite"]},
            "onedrive": {"backup": ["Files.Read.All"], "restore": ["Files.ReadWrite.All"]},
            "sharepoint": {"backup": ["Sites.Read.All"], "restore": ["Sites.ReadWrite.All"]},
            "teams": {"backup": ["Chat.Read.All", "ChannelMessage.Read.All", "Team.ReadBasic.All"], "restore": []},
            "entra_id": {"backup": ["Directory.Read.All", "User.Read.All", "Group.Read.All"], "restore": ["User.ReadWrite.All", "Group.ReadWrite.All", "Application.ReadWrite.All"]},
        }

        result = {}
        for workload, perms in workload_perms.items():
            backup_granted = all(p in granted_permissions for p in perms["backup"])
            restore_granted = all(p in granted_permissions for p in perms["restore"]) if perms["restore"] else None

            result[workload] = {
                "backup": backup_granted,
                "restore": restore_granted,
                "missing_backup": [p for p in perms["backup"] if p not in granted_permissions],
                "missing_restore": [p for p in perms["restore"] if p not in granted_permissions] if perms["restore"] else [],
            }

        return {
            "total_granted": len(granted_permissions),
            "total_required": len(BACKUP_PERMISSIONS),
            "all_backup_ready": all(r["backup"] for r in result.values()),
            "workloads": result,
        }


# Singleton
app_provisioning = AppProvisioningService()
