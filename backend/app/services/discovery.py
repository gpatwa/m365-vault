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

    async def _get_graph_client(self, tenant: Tenant, workload: str) -> GraphClient:
        """Get Graph client for discovery using per-workload credentials."""
        from app.services.credential_resolver import get_graph_client
        return await get_graph_client(self.db, tenant, workload, access_mode="backup")

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
        """Run full discovery for a tenant. Returns counts.

        Uses per-workload graph clients: each workload type gets its own
        Entra app with only the permissions it needs. The entra_id app has
        User.Read.All for user enumeration, while exchange app has Mail.Read
        for mailbox validation, etc.
        """
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

        # Get per-workload graph clients (fall back to entra_id if specific app not configured)
        graph_entra = await self._get_graph_client(tenant, "entra_id")

        # Exchange needs Mail.Read — use exchange app
        try:
            graph_exchange = await self._get_graph_client(tenant, "exchange")
        except Exception:
            graph_exchange = graph_entra  # Fallback (legacy single-app)
            logger.info("Exchange workload app not configured, falling back to entra_id app")

        # Get user list using entra_id app (has User.Read.All)
        try:
            users = await graph_entra.get_all_pages("/users", params={
                "$select": "id,displayName,mail,userPrincipalName,assignedLicenses",
                "$filter": "assignedLicenses/$count ne 0&$count=true",
                "$top": "999",
            })
        except Exception as e:
            # Fallback without filter if $count fails
            logger.warning(f"User discovery with filter failed, retrying without filter: {e}")
            try:
                users = await graph_entra.get_all_pages("/users", params={
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

            # Validate Exchange mailbox exists using exchange app (needs Mail.Read)
            try:
                await graph_exchange.get(f"/users/{user_id}/mailFolders", params={
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

        # Discover shared mailboxes (Professional+ feature)
        from app.services.feature_flags import feature_flags
        if feature_flags.is_enabled("shared_mailbox"):
            try:
                # Shared mailboxes are users with recipientType = SharedMailbox
                # They often don't have licenses but do have mailboxes
                shared_users = await graph_entra.get_all_pages("/users", params={
                    "$select": "id,displayName,mail,userPrincipalName,userType",
                    "$filter": "mail ne null",
                    "$top": "999",
                })
                for su in shared_users:
                    su_id = su.get("id")
                    if su_id in discovered_ids.get("exchange", set()):
                        continue  # Already discovered as regular mailbox
                    su_name = su.get("displayName", "Unknown")
                    su_email = su.get("mail")
                    if not su_email:
                        continue
                    # Check if it has a mailbox using exchange app (needs Mail.Read)
                    try:
                        await graph_exchange.get(f"/users/{su_id}/mailFolders", params={"$select": "id", "$top": "1"})
                        await self._upsert_protected_object(
                            tenant_id=tenant.id,
                            workload_type=WorkloadType.EXCHANGE,
                            ms_object_id=su_id,
                            display_name=f"{su_name} (Shared Mailbox)",
                            email=su_email,
                            user_principal_name=su.get("userPrincipalName"),
                            metadata={"source": "shared_mailbox_discovery", "mailbox_type": "shared"},
                            object_subtype="shared_mailbox",
                        )
                        discovered_ids.setdefault("exchange", set()).add(su_id)
                        results["mailboxes"] += 1
                        logger.info(f"Discovered shared mailbox: {su_name}")
                    except Exception:
                        pass  # Not a shared mailbox or no access
            except Exception as e:
                logger.warning(f"Shared mailbox discovery failed: {e}")

        # OneDrive needs Files.Read.All — use onedrive app
        try:
            graph_onedrive = await self._get_graph_client(tenant, "onedrive")
        except Exception:
            graph_onedrive = graph_entra  # Fallback (legacy single-app)
            logger.info("OneDrive workload app not configured, falling back to entra_id app")

        # Validate OneDrive for each user
        for user in users:
            user_id = user.get("id")
            display_name = user.get("displayName", "Unknown")
            email = user.get("mail") or user.get("userPrincipalName")
            upn = user.get("userPrincipalName")
            if not email:
                continue

            # Validate OneDrive is provisioned (drive/root fails if no mysite)
            try:
                await graph_onedrive.get(f"/users/{user_id}/drive/root", params={
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

        # SharePoint needs Sites.Read.All — use sharepoint app
        try:
            graph_sharepoint = await self._get_graph_client(tenant, "sharepoint")
        except Exception:
            graph_sharepoint = graph_entra  # Fallback
            logger.info("SharePoint workload app not configured, falling back to entra_id app")

        # Discover SharePoint sites via multiple methods
        discovered_site_ids = set()

        # Method 1: Try /sites/getAllSites (requires Sites.Read.All)
        try:
            sites = await graph_sharepoint.get_all_pages("/sites/getAllSites", params={
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
                sites = await graph_sharepoint.get_all_pages("/sites", params={
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
                groups = await graph_sharepoint.get_all_pages("/groups", params={
                    "$filter": "groupTypes/any(g:g eq 'Unified')",
                    "$select": "id,displayName",
                    "$top": "999",
                })
                for group in groups:
                    try:
                        site_data = await graph_sharepoint.get(f"/groups/{group['id']}/sites/root", params={
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

        # Teams needs Chat.Read.All etc — use teams app
        try:
            graph_teams = await self._get_graph_client(tenant, "teams")
        except Exception:
            graph_teams = graph_entra  # Fallback
            logger.info("Teams workload app not configured, falling back to entra_id app")

        # Discover Microsoft Teams
        try:
            teams_count, teams_ids = await self._discover_teams(tenant, graph_teams)
            discovered_ids["teams"] = teams_ids
            results["teams"] = teams_count
        except Exception as e:
            results["errors"].append(f"Teams discovery failed: {str(e)}")

        # Discover Entra ID directory objects (uses entra_id app)
        try:
            entra_count = await self._discover_entra_id(tenant, graph_entra)
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
        """Discover only specific workloads using per-workload graph clients."""
        # Use entra_id app for user enumeration (has User.Read.All)
        graph_entra = await self._get_graph_client(tenant, "entra_id")
        results = {
            "mailboxes": 0, "onedrives": 0, "sites": 0,
            "teams": 0, "entra_objects": 0, "removed": 0, "errors": [],
        }

        # Get users if Exchange or OneDrive requested
        users = []
        if "exchange" in workloads or "onedrive" in workloads:
            try:
                users = await graph_entra.get_all_pages("/users", params={
                    "$select": "id,displayName,mail,userPrincipalName",
                    "$top": "999",
                })
            except Exception as e:
                results["errors"].append(f"User discovery failed: {str(e)}")

        # Exchange — use exchange app (needs Mail.Read)
        if "exchange" in workloads:
            try:
                graph_exchange = await self._get_graph_client(tenant, "exchange")
            except Exception:
                graph_exchange = graph_entra
            for user in users:
                user_id = user.get("id")
                display_name = user.get("displayName", "Unknown")
                email = user.get("mail") or user.get("userPrincipalName")
                if not email:
                    continue
                try:
                    await graph_exchange.get(f"/users/{user_id}/mailFolders", params={"$select": "id", "$top": "1"})
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

        # OneDrive — use onedrive app (needs Files.Read.All)
        if "onedrive" in workloads:
            try:
                graph_onedrive = await self._get_graph_client(tenant, "onedrive")
            except Exception:
                graph_onedrive = graph_entra
            for user in users:
                user_id = user.get("id")
                display_name = user.get("displayName", "Unknown")
                email = user.get("mail") or user.get("userPrincipalName")
                if not email:
                    continue
                try:
                    await graph_onedrive.get(f"/users/{user_id}/drive/root", params={"$select": "id,name"})
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

        # SharePoint — use sharepoint app (needs Sites.Read.All)
        if "sharepoint" in workloads:
            try:
                graph_sharepoint = await self._get_graph_client(tenant, "sharepoint")
            except Exception:
                graph_sharepoint = graph_entra
            try:
                sites = await graph_sharepoint.get_all_pages("/sites/getAllSites", params={
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

        # Teams — use teams app (needs Chat.Read.All etc)
        if "teams" in workloads:
            try:
                graph_teams = await self._get_graph_client(tenant, "teams")
            except Exception:
                graph_teams = graph_entra
            try:
                teams_count, _ = await self._discover_teams(tenant, graph_teams)
                results["teams"] = teams_count
            except Exception as e:
                results["errors"].append(f"Teams discovery failed: {str(e)}")

        # Entra ID
        if "entra_id" in workloads:
            try:
                entra_count = await self._discover_entra_id(tenant, graph_entra)
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
        object_subtype: str = None,
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
            if object_subtype:
                obj.object_subtype = object_subtype
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
                object_subtype=object_subtype,
                status=ProtectionStatus.UNPROTECTED,
                metadata_json=json.dumps(metadata) if metadata else None,
            )
            self.db.add(obj)

        await self.db.flush()
