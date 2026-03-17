"""M365 object discovery service.

Discovers all Exchange mailboxes, OneDrive accounts, and SharePoint sites
from the M365 tenant via the Graph API.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject, WorkloadType, ProtectionStatus
from app.models.tenant import Tenant, TenantStatus
from app.services.graph_client import GraphClient
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Discovers M365 objects and syncs to local database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_graph_client(self, tenant: Tenant) -> GraphClient:
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
        )

    async def discover_all(self, tenant: Tenant) -> dict:
        """Run full discovery for a tenant. Returns counts."""
        graph = self._get_graph_client(tenant)
        results = {
            "mailboxes": 0,
            "onedrives": 0,
            "sites": 0,
            "errors": [],
        }

        # Discover Exchange mailboxes and OneDrive accounts (from users)
        try:
            users = await graph.get_all_pages("/users", params={
                "$select": "id,displayName,mail,userPrincipalName,assignedLicenses",
                "$filter": "assignedLicenses/$count ne 0&$count=true",
                "$top": "999",
            })
        except Exception as e:
            # Fallback without filter if $count fails
            logger.warning(f"User discovery with filter failed, retrying without filter: {e}")
            try:
                users = await graph.get_all_pages("/users", params={
                    "$select": "id,displayName,mail,userPrincipalName",
                    "$top": "999",
                })
            except Exception as e2:
                results["errors"].append(f"User discovery failed: {str(e2)}")
                users = []

        for user in users:
            user_id = user.get("id")
            display_name = user.get("displayName", "Unknown")
            email = user.get("mail") or user.get("userPrincipalName")
            upn = user.get("userPrincipalName")

            if not email:
                continue

            # Exchange mailbox
            await self._upsert_protected_object(
                tenant_id=tenant.id,
                workload_type=WorkloadType.EXCHANGE,
                ms_object_id=user_id,
                display_name=f"{display_name} (Mailbox)",
                email=email,
                user_principal_name=upn,
                metadata={"source": "user_discovery"},
            )
            results["mailboxes"] += 1

            # OneDrive account
            await self._upsert_protected_object(
                tenant_id=tenant.id,
                workload_type=WorkloadType.ONEDRIVE,
                ms_object_id=user_id,
                display_name=f"{display_name} (OneDrive)",
                email=email,
                user_principal_name=upn,
                metadata={"source": "user_discovery"},
            )
            results["onedrives"] += 1

        # Discover SharePoint sites via multiple methods
        discovered_site_ids = set()

        # Method 1: Try /sites/getAllSites (requires Sites.Read.All)
        try:
            sites = await graph.get_all_pages("/sites/getAllSites", params={
                "$select": "id,displayName,webUrl,name",
                "$top": "999",
            })
            for site in sites:
                site_id = site.get("id")
                if site_id and site_id not in discovered_site_ids:
                    display_name = site.get("displayName", site.get("name", "Unknown"))
                    web_url = site.get("webUrl", "")
                    # Skip personal sites (OneDrive) and search/admin sites
                    if "/personal/" in web_url or "-admin." in web_url or "-my." in web_url:
                        continue
                    discovered_site_ids.add(site_id)
                    await self._upsert_protected_object(
                        tenant_id=tenant.id,
                        workload_type=WorkloadType.SHAREPOINT,
                        ms_object_id=site_id,
                        display_name=f"{display_name} (SharePoint)",
                        site_url=web_url,
                        metadata={"webUrl": web_url, "source": "site_discovery"},
                    )
                    results["sites"] += 1
        except Exception as e:
            logger.warning(f"getAllSites failed: {e}, trying fallback methods")

        # Method 2: Try search-based discovery
        if not discovered_site_ids:
            try:
                sites = await graph.get_all_pages("/sites", params={
                    "search": "*",
                    "$select": "id,displayName,webUrl,name",
                    "$top": "999",
                })
                for site in sites:
                    site_id = site.get("id")
                    if site_id and site_id not in discovered_site_ids:
                        display_name = site.get("displayName", site.get("name", "Unknown"))
                        web_url = site.get("webUrl", "")
                        if "/personal/" in web_url or "-admin." in web_url or "-my." in web_url:
                            continue
                        discovered_site_ids.add(site_id)
                        await self._upsert_protected_object(
                            tenant_id=tenant.id,
                            workload_type=WorkloadType.SHAREPOINT,
                            ms_object_id=site_id,
                            display_name=f"{display_name} (SharePoint)",
                            site_url=web_url,
                            metadata={"webUrl": web_url, "source": "site_discovery"},
                        )
                        results["sites"] += 1
            except Exception as e:
                logger.warning(f"Site search failed: {e}")

        # Method 3: Discover sites via M365 groups
        if not discovered_site_ids:
            try:
                groups = await graph.get_all_pages("/groups", params={
                    "$filter": "groupTypes/any(g:g eq 'Unified')",
                    "$select": "id,displayName",
                    "$top": "999",
                })
                for group in groups:
                    try:
                        site_data = await graph.get(f"/groups/{group['id']}/sites/root", params={
                            "$select": "id,displayName,webUrl,name",
                        })
                        site_id = site_data.get("id")
                        if site_id and site_id not in discovered_site_ids:
                            display_name = site_data.get("displayName", group.get("displayName", "Unknown"))
                            web_url = site_data.get("webUrl", "")
                            discovered_site_ids.add(site_id)
                            await self._upsert_protected_object(
                                tenant_id=tenant.id,
                                workload_type=WorkloadType.SHAREPOINT,
                                ms_object_id=site_id,
                                display_name=f"{display_name} (SharePoint)",
                                site_url=web_url,
                                metadata={"webUrl": web_url, "source": "group_discovery", "groupId": group["id"]},
                            )
                            results["sites"] += 1
                    except Exception:
                        continue
            except Exception as e:
                results["errors"].append(f"SharePoint discovery failed: {str(e)}")

        # Update tenant counts
        tenant.total_mailboxes = results["mailboxes"]
        tenant.total_onedrives = results["onedrives"]
        tenant.total_sites = results["sites"]
        tenant.last_discovery_at = datetime.utcnow()
        tenant.status = TenantStatus.ACTIVE
        await self.db.commit()

        logger.info(
            f"Discovery complete for tenant {tenant.name}: "
            f"{results['mailboxes']} mailboxes, {results['onedrives']} OneDrives, "
            f"{results['sites']} SharePoint sites"
        )
        return results

    async def _upsert_protected_object(
        self,
        tenant_id: int,
        workload_type: WorkloadType,
        ms_object_id: str,
        display_name: str,
        email: str = None,
        user_principal_name: str = None,
        site_url: str = None,
        metadata: dict = None,
    ):
        """Insert or update a protected object."""
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == workload_type,
                ProtectedObject.ms_object_id == ms_object_id,
            )
        )
        obj = result.scalar_one_or_none()

        if obj:
            obj.display_name = display_name
            obj.email = email
            obj.user_principal_name = user_principal_name
            obj.site_url = site_url
            obj.metadata_json = json.dumps(metadata) if metadata else obj.metadata_json
            obj.updated_at = datetime.utcnow()
        else:
            obj = ProtectedObject(
                tenant_id=tenant_id,
                workload_type=workload_type,
                ms_object_id=ms_object_id,
                display_name=display_name,
                email=email,
                user_principal_name=user_principal_name,
                site_url=site_url,
                status=ProtectionStatus.UNPROTECTED,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            self.db.add(obj)

        await self.db.flush()
