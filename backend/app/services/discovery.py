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

    async def discover_all(self, tenant: Tenant, workloads: list[str] = None) -> dict:
        """Run discovery for a tenant. Optionally filter to specific workloads.

        Args:
            workloads: Optional list like ["exchange", "entra_id"]. None = discover all.
        """
        # Demo tenants use simulated discovery (no real Graph API)
        if tenant.ms_tenant_id and tenant.ms_tenant_id.startswith("demo-"):
            return await self._discover_demo(tenant, set(workloads) if workloads else None)

        if workloads:
            return await self._discover_filtered(tenant, set(workloads))
        return await self._discover_all_workloads(tenant)

    async def _discover_demo(self, tenant: Tenant, workloads: set[str] | None) -> dict:
        """Simulated discovery for demo tenants — creates realistic fake objects."""
        import random
        demo_names = [
            ("Sarah Chen", "sarahc"), ("Marcus Johnson", "marcusj"), ("Emily Rodriguez", "emilyr"),
            ("David Kim", "davidk"), ("Lisa Thompson", "lisat"), ("James Wilson", "jamesw"),
            ("Priya Patel", "priyap"), ("Alex Turner", "alext"), ("Rachel Lee", "rachell"),
            ("Tom Nakamura", "tomn"), ("Fatima Al-Zahra", "fatimaz"), ("Ben Cooper", "benc"),
            ("Mia Santos", "mias"), ("Jake Morrison", "jakem"), ("Olga Petrov", "olgap"),
        ]
        site_names = ["Marketing Hub", "Engineering Wiki", "Sales Pipeline", "HR Portal", "Finance Reports", "Executive Dashboard"]
        team_names = ["Engineering", "Marketing", "Sales", "Leadership", "All Hands"]
        domain = tenant.name.lower().replace(" ", "") + ".com"
        all_workloads = workloads or {"exchange", "onedrive", "sharepoint", "teams", "entra_id"}
        results = {"mailboxes": 0, "onedrives": 0, "sites": 0, "teams": 0, "entra_objects": 0, "removed": 0, "errors": []}

        for name, login in demo_names:
            email = f"{login}@{domain}"
            ext_id = f"demo-user-{login}"

            if "exchange" in all_workloads:
                existing = await self.db.execute(
                    select(ProtectedObject).where(ProtectedObject.tenant_id == tenant.id, ProtectedObject.ms_object_id == ext_id, ProtectedObject.workload_type == WorkloadType.EXCHANGE)
                )
                if not existing.scalar_one_or_none():
                    self.db.add(ProtectedObject(tenant_id=tenant.id, ms_object_id=ext_id, display_name=name, email=email, workload_type=WorkloadType.EXCHANGE, status=ProtectionStatus.UNPROTECTED))
                results["mailboxes"] += 1

            if "onedrive" in all_workloads:
                od_id = f"demo-drive-{login}"
                existing = await self.db.execute(
                    select(ProtectedObject).where(ProtectedObject.tenant_id == tenant.id, ProtectedObject.ms_object_id == od_id, ProtectedObject.workload_type == WorkloadType.ONEDRIVE)
                )
                if not existing.scalar_one_or_none():
                    self.db.add(ProtectedObject(tenant_id=tenant.id, ms_object_id=od_id, display_name=f"{name}'s OneDrive", email=email, workload_type=WorkloadType.ONEDRIVE, status=ProtectionStatus.UNPROTECTED))
                results["onedrives"] += 1

        if "sharepoint" in all_workloads:
            for site in site_names:
                sp_id = f"demo-site-{site.lower().replace(' ', '-')}"
                existing = await self.db.execute(
                    select(ProtectedObject).where(ProtectedObject.tenant_id == tenant.id, ProtectedObject.ms_object_id == sp_id, ProtectedObject.workload_type == WorkloadType.SHAREPOINT)
                )
                if not existing.scalar_one_or_none():
                    self.db.add(ProtectedObject(tenant_id=tenant.id, ms_object_id=sp_id, display_name=site, workload_type=WorkloadType.SHAREPOINT, status=ProtectionStatus.UNPROTECTED))
                results["sites"] += 1

        if "teams" in all_workloads:
            for team in team_names:
                t_id = f"demo-team-{team.lower().replace(' ', '-')}"
                existing = await self.db.execute(
                    select(ProtectedObject).where(ProtectedObject.tenant_id == tenant.id, ProtectedObject.ms_object_id == t_id, ProtectedObject.workload_type == WorkloadType.TEAMS)
                )
                if not existing.scalar_one_or_none():
                    self.db.add(ProtectedObject(tenant_id=tenant.id, ms_object_id=t_id, display_name=team, workload_type=WorkloadType.TEAMS, status=ProtectionStatus.UNPROTECTED))
                results["teams"] += 1

        if "entra_id" in all_workloads:
            entra_objects = [("Users", 15), ("Groups", 8), ("Roles", 3)]
            for obj_type, count in entra_objects:
                e_id = f"demo-entra-{obj_type.lower()}"
                existing = await self.db.execute(
                    select(ProtectedObject).where(ProtectedObject.tenant_id == tenant.id, ProtectedObject.ms_object_id == e_id, ProtectedObject.workload_type == WorkloadType.ENTRA_ID)
                )
                if not existing.scalar_one_or_none():
                    self.db.add(ProtectedObject(tenant_id=tenant.id, ms_object_id=e_id, display_name=f"Entra {obj_type} ({count})", workload_type=WorkloadType.ENTRA_ID, status=ProtectionStatus.UNPROTECTED))
                results["entra_objects"] += count

        # Update tenant counts
        tenant.total_mailboxes = results["mailboxes"]
        tenant.total_onedrives = results["onedrives"]
        tenant.total_sites = results["sites"]
        tenant.total_teams = results["teams"]
        tenant.total_entra_objects = results["entra_objects"]
        tenant.status = TenantStatus.ACTIVE

        logger.info(f"Demo discovery for {tenant.name}: {results}")
        return results

    async def _discover_all_workloads(self, tenant: Tenant) -> dict:
        """Run full discovery for a tenant. Returns counts."""
        graph = self._get_graph_client(tenant)
        results = {
            "mailboxes": 0,
            "onedrives": 0,
            "sites": 0,
            "teams": 0,
            "entra_objects": 0,
            "removed": 0,
            "errors": [],
        }
        # Track discovered object IDs to clean up stale entries
        discovered_ids = {"exchange": set(), "onedrive": set(), "sharepoint": set(), "teams": set(), "entra_id": set()}

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

            # Validate Exchange mailbox exists (mailFolders fails if no mailbox)
            try:
                await graph.get(f"/users/{user_id}/mailFolders", params={
                    "$select": "id",
                    "$top": "1",
                })
                await self._upsert_protected_object(
                    tenant_id=tenant.id,
                    workload_type=WorkloadType.EXCHANGE,
                    ms_object_id=user_id,
                    display_name=f"{display_name} (Mailbox)",
                    email=email,
                    user_principal_name=upn,
                    metadata={"source": "user_discovery"},
                )
                discovered_ids["exchange"].add(user_id)
                results["mailboxes"] += 1
            except Exception as e:
                logger.info(f"Skipping Exchange for {display_name}: {e}")

            # Validate OneDrive is provisioned (drive/root fails if no mysite)
            try:
                await graph.get(f"/users/{user_id}/drive/root", params={
                    "$select": "id,name",
                })
                await self._upsert_protected_object(
                    tenant_id=tenant.id,
                    workload_type=WorkloadType.ONEDRIVE,
                    ms_object_id=user_id,
                    display_name=f"{display_name} (OneDrive)",
                    email=email,
                    user_principal_name=upn,
                    metadata={"source": "user_discovery"},
                )
                discovered_ids["onedrive"].add(user_id)
                results["onedrives"] += 1
            except Exception as e:
                logger.info(f"Skipping OneDrive for {display_name}: {e}")

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

        # Discover Microsoft Teams
        try:
            teams_count, teams_ids = await self._discover_teams(tenant, graph)
            discovered_ids["teams"] = teams_ids
            results["teams"] = teams_count
        except Exception as e:
            results["errors"].append(f"Teams discovery failed: {str(e)}")

        # Discover Entra ID directory objects
        try:
            entra_count = await self._discover_entra_id(tenant, graph)
            discovered_ids["entra_id"].add(tenant.ms_tenant_id)
            results["entra_objects"] = entra_count
        except Exception as e:
            results["errors"].append(f"Entra ID discovery failed: {str(e)}")

        # Remove stale protected objects that no longer exist
        workload_map = {
            WorkloadType.EXCHANGE: discovered_ids["exchange"],
            WorkloadType.ONEDRIVE: discovered_ids["onedrive"],
            WorkloadType.SHAREPOINT: discovered_site_ids,
            WorkloadType.TEAMS: discovered_ids["teams"],
            WorkloadType.ENTRA_ID: discovered_ids["entra_id"],
        }
        for wl_type, valid_ids in workload_map.items():
            if not valid_ids:
                continue  # Skip if discovery returned nothing (possible API error)
            valid_id_list = list(valid_ids)
            logger.info(f"Cleanup {wl_type.value}: {len(valid_id_list)} valid IDs")
            stale = await self.db.execute(
                select(ProtectedObject).where(
                    ProtectedObject.tenant_id == tenant.id,
                    ProtectedObject.workload_type == wl_type,
                    ProtectedObject.ms_object_id.notin_(valid_id_list),
                )
            )
            for obj in stale.scalars().all():
                logger.warning(f"Marking stale {wl_type.value} object as ERROR: {obj.display_name} ({obj.ms_object_id})")
                obj.status = ProtectionStatus.ERROR
                obj.metadata_json = json.dumps({
                    **(json.loads(obj.metadata_json) if obj.metadata_json else {}),
                    "stale_reason": "Not found during discovery validation",
                    "marked_stale_at": datetime.utcnow().isoformat(),
                })
                results["removed"] += 1

        # Update tenant counts
        tenant.total_mailboxes = results["mailboxes"]
        tenant.total_onedrives = results["onedrives"]
        tenant.total_sites = results["sites"]
        tenant.total_teams = results.get("teams", 0)
        tenant.total_entra_objects = results.get("entra_objects", 0)
        tenant.last_discovery_at = datetime.utcnow()
        tenant.status = TenantStatus.ACTIVE
        await self.db.commit()

        logger.info(
            f"Discovery complete for tenant {tenant.name}: "
            f"{results['mailboxes']} mailboxes, {results['onedrives']} OneDrives, "
            f"{results['sites']} SharePoint sites, {results.get('entra_objects', 0)} Entra ID objects, "
            f"{results['removed']} stale removed"
        )
        return results

    async def _discover_teams(self, tenant: Tenant, graph: GraphClient) -> tuple[int, set]:
        """Discover Microsoft Teams by finding M365 groups with Teams provisioned."""
        team_ids = set()
        try:
            groups = await graph.get_all_pages("/groups", params={
                "$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')",
                "$select": "id,displayName,description,mail",
                "$top": "999",
            })
        except Exception as e:
            logger.warning(f"Teams discovery with filter failed, trying fallback: {e}")
            try:
                groups = await graph.get_all_pages("/groups", params={
                    "$filter": "groupTypes/any(g:g eq 'Unified')",
                    "$select": "id,displayName,description,mail,resourceProvisioningOptions",
                    "$top": "999",
                })
                groups = [g for g in groups if "Team" in (g.get("resourceProvisioningOptions") or [])]
            except Exception as e2:
                logger.error(f"Teams discovery fallback also failed: {e2}")
                groups = []

        for group in groups:
            group_id = group.get("id")
            display_name = group.get("displayName", "Unknown Team")

            await self._upsert_protected_object(
                tenant_id=tenant.id,
                workload_type=WorkloadType.TEAMS,
                ms_object_id=group_id,
                display_name=f"{display_name} (Team)",
                email=group.get("mail"),
                metadata={"source": "teams_discovery", "description": group.get("description")},
            )
            team_ids.add(group_id)

        # Also discover per-user chat objects for users with Teams license
        try:
            users = await graph.get_all_pages("/users", params={
                "$select": "id,displayName,mail,userPrincipalName",
                "$top": "999",
            })
            chat_count = 0
            for user in users:
                user_id = user.get("id")
                display_name = user.get("displayName", "Unknown")
                # Check if user has any chats (quick probe)
                try:
                    await graph.get(f"/users/{user_id}/chats", params={"$top": "1", "$select": "id"})
                    await self._upsert_protected_object(
                        tenant_id=tenant.id,
                        workload_type=WorkloadType.TEAMS,
                        ms_object_id=user_id,
                        display_name=f"{display_name} (Chats)",
                        email=user.get("mail") or user.get("userPrincipalName"),
                        metadata={"source": "teams_chat_discovery", "type": "user_chats"},
                    )
                    team_ids.add(user_id)
                    chat_count += 1
                except Exception:
                    pass  # User doesn't have Teams/chats access
            logger.info(f"Teams chat discovery: {chat_count} users with chat access")
        except Exception as e:
            logger.warning(f"Teams chat user discovery failed: {e}")

        logger.info(f"Teams discovery: {len(team_ids)} objects ({len(team_ids) - chat_count if 'chat_count' in dir() else 0} teams, {chat_count if 'chat_count' in dir() else 0} chat users)")
        return len(team_ids), team_ids

    async def _discover_entra_id(self, tenant: Tenant, graph: GraphClient) -> int:
        """Discover Entra ID directory objects. Creates a single ProtectedObject
        representing the entire directory for this tenant."""
        total_objects = 0

        # Count users
        try:
            users = await graph.get_all_pages("/users", params={"$select": "id", "$top": "999"})
            total_objects += len(users)
        except Exception as e:
            logger.warning(f"Entra ID user count failed: {e}")

        # Count groups
        try:
            groups = await graph.get_all_pages("/groups", params={"$select": "id", "$top": "999"})
            total_objects += len(groups)
        except Exception as e:
            logger.warning(f"Entra ID group count failed: {e}")

        # Count app registrations
        try:
            apps = await graph.get_all_pages("/applications", params={"$select": "id", "$top": "999"})
            total_objects += len(apps)
        except Exception as e:
            logger.warning(f"Entra ID app count failed: {e}")

        # Count Conditional Access policies
        try:
            policies = await graph.get_all_pages("/identity/conditionalAccess/policies", params={"$select": "id"})
            total_objects += len(policies)
        except Exception as e:
            logger.info(f"Entra ID CA policy count failed (may need P1 license): {e}")

        # Create single ProtectedObject for the directory
        await self._upsert_protected_object(
            tenant_id=tenant.id,
            workload_type=WorkloadType.ENTRA_ID,
            ms_object_id=tenant.ms_tenant_id,
            display_name=f"{tenant.name} (Entra ID)",
            metadata={
                "source": "entra_id_discovery",
                "total_objects": total_objects,
            },
        )

        logger.info(f"Entra ID discovery: {total_objects} directory objects")
        return total_objects

    async def _discover_filtered(self, tenant: Tenant, workloads: set[str]) -> dict:
        """Discover only specific workloads. Calls individual discovery methods."""
        graph = self._get_graph_client(tenant)
        results = {
            "mailboxes": 0, "onedrives": 0, "sites": 0,
            "teams": 0, "entra_objects": 0, "removed": 0, "errors": [],
        }

        # Get users if Exchange or OneDrive requested
        users = []
        if "exchange" in workloads or "onedrive" in workloads:
            try:
                users = await graph.get_all_pages("/users", params={
                    "$select": "id,displayName,mail,userPrincipalName",
                    "$top": "999",
                })
            except Exception as e:
                results["errors"].append(f"User discovery failed: {str(e)}")

        # Exchange
        if "exchange" in workloads:
            for user in users:
                user_id = user.get("id")
                display_name = user.get("displayName", "Unknown")
                email = user.get("mail") or user.get("userPrincipalName")
                if not email:
                    continue
                try:
                    await graph.get(f"/users/{user_id}/mailFolders", params={"$select": "id", "$top": "1"})
                    await self._upsert_protected_object(
                        tenant_id=tenant.id, workload_type=WorkloadType.EXCHANGE,
                        ms_object_id=user_id, display_name=f"{display_name} (Mailbox)",
                        email=email, user_principal_name=user.get("userPrincipalName"),
                        metadata={"source": "filtered_discovery"},
                    )
                    results["mailboxes"] += 1
                except Exception:
                    pass
            logger.info(f"Filtered discovery: {results['mailboxes']} Exchange mailboxes")

        # OneDrive
        if "onedrive" in workloads:
            for user in users:
                user_id = user.get("id")
                display_name = user.get("displayName", "Unknown")
                email = user.get("mail") or user.get("userPrincipalName")
                if not email:
                    continue
                try:
                    await graph.get(f"/users/{user_id}/drive/root", params={"$select": "id,name"})
                    await self._upsert_protected_object(
                        tenant_id=tenant.id, workload_type=WorkloadType.ONEDRIVE,
                        ms_object_id=user_id, display_name=f"{display_name} (OneDrive)",
                        email=email, user_principal_name=user.get("userPrincipalName"),
                        metadata={"source": "filtered_discovery"},
                    )
                    results["onedrives"] += 1
                except Exception:
                    pass
            logger.info(f"Filtered discovery: {results['onedrives']} OneDrive accounts")

        # SharePoint
        if "sharepoint" in workloads:
            try:
                sites = await graph.get_all_pages("/sites/getAllSites", params={
                    "$select": "id,displayName,webUrl,name", "$top": "999",
                })
                for site in sites:
                    web_url = site.get("webUrl", "")
                    if "/personal/" in web_url or "-admin." in web_url or "-my." in web_url:
                        continue
                    await self._upsert_protected_object(
                        tenant_id=tenant.id, workload_type=WorkloadType.SHAREPOINT,
                        ms_object_id=site["id"],
                        display_name=f"{site.get('displayName', 'Unknown')} (SharePoint)",
                        site_url=web_url, metadata={"source": "filtered_discovery"},
                    )
                    results["sites"] += 1
            except Exception as e:
                results["errors"].append(f"SharePoint discovery failed: {str(e)}")
            logger.info(f"Filtered discovery: {results['sites']} SharePoint sites")

        # Teams
        if "teams" in workloads:
            try:
                teams_count, _ = await self._discover_teams(tenant, graph)
                results["teams"] = teams_count
            except Exception as e:
                results["errors"].append(f"Teams discovery failed: {str(e)}")

        # Entra ID
        if "entra_id" in workloads:
            try:
                entra_count = await self._discover_entra_id(tenant, graph)
                results["entra_objects"] = entra_count
            except Exception as e:
                results["errors"].append(f"Entra ID discovery failed: {str(e)}")

        # Update tenant counts for discovered workloads
        if "exchange" in workloads:
            tenant.total_mailboxes = results["mailboxes"]
        if "onedrive" in workloads:
            tenant.total_onedrives = results["onedrives"]
        if "sharepoint" in workloads:
            tenant.total_sites = results["sites"]
        if "teams" in workloads:
            tenant.total_teams = results.get("teams", 0)
        if "entra_id" in workloads:
            tenant.total_entra_objects = results.get("entra_objects", 0)

        tenant.last_discovery_at = datetime.utcnow()
        tenant.status = TenantStatus.ACTIVE
        await self.db.commit()

        logger.info(f"Filtered discovery complete for {tenant.name}: workloads={workloads}, results={results}")
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
