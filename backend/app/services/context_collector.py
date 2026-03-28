"""Organizational Context Collector — syncs user/site context from Microsoft Graph."""
import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.org_context import UserContext, SiteContext
from app.services.graph_client import GraphClient
from app.services.encryption import encryption_service

logger = logging.getLogger(__name__)


class ContextCollectorService:
    """Collects organizational context from Microsoft Graph for a tenant."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_graph_client(self, tenant: Tenant) -> GraphClient:
        client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=tenant.client_id,
            client_secret=client_secret,
        )

    async def collect_all(self, tenant: Tenant) -> dict:
        """Run full context collection for a tenant. Returns summary."""
        graph = self._get_graph_client(tenant)
        now = datetime.utcnow()
        results = {"users_synced": 0, "sites_synced": 0, "errors": []}

        # Collect user hierarchy
        try:
            results["users_synced"] = await self._collect_user_hierarchy(tenant, graph, now)
        except Exception as e:
            logger.error(f"User hierarchy collection failed for tenant {tenant.id}: {e}")
            results["errors"].append(f"User hierarchy: {str(e)[:100]}")

        # Collect privileged roles
        try:
            await self._collect_privileged_roles(tenant, graph)
        except Exception as e:
            logger.warning(f"Privileged role collection failed for tenant {tenant.id}: {e}")
            results["errors"].append(f"Privileged roles: {str(e)[:100]}")

        # Collect direct reports counts
        try:
            await self._collect_direct_reports(tenant, graph)
        except Exception as e:
            logger.warning(f"Direct reports collection failed for tenant {tenant.id}: {e}")

        # Collect sign-in activity (optional — requires AuditLog.Read.All)
        try:
            await self._collect_sign_in_activity(tenant, graph)
        except Exception as e:
            logger.info(f"Sign-in activity not available for tenant {tenant.id} (may need AuditLog.Read.All): {e}")

        # Collect site context from protected objects
        try:
            results["sites_synced"] = await self._collect_site_context(tenant, now)
        except Exception as e:
            logger.warning(f"Site context collection failed for tenant {tenant.id}: {e}")

        # Link to protected objects
        await self._link_protected_objects(tenant)
        await self.db.commit()

        return results

    async def _collect_user_hierarchy(self, tenant: Tenant, graph: GraphClient, now: datetime) -> int:
        """Sync user hierarchy from Graph: names, titles, departments, managers."""
        users = await graph.get_all_pages(
            "/users",
            params={
                "$select": "id,displayName,mail,jobTitle,department,officeLocation,userPrincipalName",
                "$top": "999",
            },
        )

        count = 0
        for user in users:
            ms_user_id = user.get("id")
            if not ms_user_id:
                continue

            # Upsert UserContext
            existing = await self.db.execute(
                select(UserContext).where(
                    UserContext.tenant_id == tenant.id,
                    UserContext.ms_user_id == ms_user_id,
                )
            )
            ctx = existing.scalar_one_or_none()

            if ctx:
                ctx.display_name = user.get("displayName", ctx.display_name)
                ctx.email = user.get("mail", ctx.email)
                ctx.job_title = user.get("jobTitle")
                ctx.department = user.get("department")
                ctx.office_location = user.get("officeLocation")
                ctx.raw_graph_data = json.dumps(user, default=str)
                ctx.synced_at = now
            else:
                ctx = UserContext(
                    tenant_id=tenant.id,
                    ms_user_id=ms_user_id,
                    display_name=user.get("displayName", "Unknown"),
                    email=user.get("mail"),
                    job_title=user.get("jobTitle"),
                    department=user.get("department"),
                    office_location=user.get("officeLocation"),
                    raw_graph_data=json.dumps(user, default=str),
                    synced_at=now,
                )
                self.db.add(ctx)

            count += 1

        await self.db.flush()

        # Collect managers via batch (up to 5 levels)
        await self._collect_managers(tenant, graph)

        return count

    async def _collect_managers(self, tenant: Tenant, graph: GraphClient):
        """Collect manager chain for each user."""
        result = await self.db.execute(
            select(UserContext).where(UserContext.tenant_id == tenant.id)
        )
        users = {u.ms_user_id: u for u in result.scalars().all()}

        for ms_id, ctx in users.items():
            try:
                mgr_resp = await graph.get(f"/users/{ms_id}/manager", params={"$select": "id,displayName"})
                if mgr_resp and mgr_resp.get("id"):
                    ctx.manager_ms_id = mgr_resp["id"]

                    # Build manager chain (up to 5 levels)
                    chain = []
                    current_mgr_id = mgr_resp["id"]
                    for _ in range(5):
                        if not current_mgr_id or current_mgr_id in chain:
                            break
                        chain.append(current_mgr_id)
                        if current_mgr_id in users:
                            current_mgr_id = users[current_mgr_id].manager_ms_id
                        else:
                            break
                    ctx.manager_chain = json.dumps(chain)
            except Exception:
                # No manager (top of org) or permission issue — skip
                pass

        await self.db.flush()

    async def _collect_privileged_roles(self, tenant: Tenant, graph: GraphClient):
        """Detect Global Admins and other privileged role holders."""
        try:
            roles = await graph.get_all_pages("/directoryRoles", params={"$select": "id,displayName"})
        except Exception:
            logger.info("directoryRoles not accessible — skipping privileged role detection")
            return

        privileged_role_names = {
            "Global Administrator", "Privileged Role Administrator",
            "Security Administrator", "Exchange Administrator",
            "SharePoint Administrator", "Teams Administrator",
            "User Administrator", "Conditional Access Administrator",
            "Application Administrator", "Cloud Application Administrator",
        }

        for role in roles:
            role_name = role.get("displayName", "")
            role_id = role.get("id")
            if not role_id:
                continue

            is_global_admin = role_name == "Global Administrator"
            is_privileged = role_name in privileged_role_names

            if not is_privileged:
                continue

            try:
                members = await graph.get_all_pages(
                    f"/directoryRoles/{role_id}/members",
                    params={"$select": "id"},
                )
            except Exception:
                continue

            for member in members:
                member_id = member.get("id")
                if not member_id:
                    continue

                result = await self.db.execute(
                    select(UserContext).where(
                        UserContext.tenant_id == tenant.id,
                        UserContext.ms_user_id == member_id,
                    )
                )
                ctx = result.scalar_one_or_none()
                if ctx:
                    ctx.has_privileged_role = 1
                    if is_global_admin:
                        ctx.is_global_admin = 1
                    # Append role name to privileged_roles list
                    existing_roles = json.loads(ctx.privileged_roles) if ctx.privileged_roles else []
                    if role_name not in existing_roles:
                        existing_roles.append(role_name)
                        ctx.privileged_roles = json.dumps(existing_roles)

        await self.db.flush()

    async def _collect_direct_reports(self, tenant: Tenant, graph: GraphClient):
        """Count direct reports for each user."""
        result = await self.db.execute(
            select(UserContext).where(UserContext.tenant_id == tenant.id)
        )
        users = result.scalars().all()

        for ctx in users:
            try:
                reports = await graph.get_all_pages(
                    f"/users/{ctx.ms_user_id}/directReports",
                    params={"$select": "id"},
                )
                ctx.direct_reports_count = len(reports) if reports else 0
            except Exception:
                ctx.direct_reports_count = 0

        await self.db.flush()

    async def _collect_sign_in_activity(self, tenant: Tenant, graph: GraphClient):
        """Collect last sign-in dates (requires AuditLog.Read.All)."""
        try:
            users = await graph.get_all_pages(
                "/users",
                params={
                    "$select": "id,signInActivity",
                    "$top": "999",
                },
            )
        except Exception:
            logger.info("signInActivity not available — AuditLog.Read.All likely not consented")
            return

        for user in users:
            ms_id = user.get("id")
            sign_in = user.get("signInActivity", {})
            last_sign_in = sign_in.get("lastSignInDateTime") if sign_in else None

            if ms_id and last_sign_in:
                result = await self.db.execute(
                    select(UserContext).where(
                        UserContext.tenant_id == tenant.id,
                        UserContext.ms_user_id == ms_id,
                    )
                )
                ctx = result.scalar_one_or_none()
                if ctx:
                    try:
                        ctx.last_sign_in_at = datetime.fromisoformat(last_sign_in.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        pass

        await self.db.flush()

    async def _collect_site_context(self, tenant: Tenant, now: datetime) -> int:
        """Populate site context from existing protected SharePoint objects."""
        result = await self.db.execute(
            select(ProtectedObject).where(
                ProtectedObject.tenant_id == tenant.id,
                ProtectedObject.workload_type == WorkloadType.SHAREPOINT,
            )
        )
        sites = result.scalars().all()
        count = 0

        for site in sites:
            existing = await self.db.execute(
                select(SiteContext).where(
                    SiteContext.tenant_id == tenant.id,
                    SiteContext.ms_site_id == site.ms_object_id,
                )
            )
            ctx = existing.scalar_one_or_none()

            if ctx:
                ctx.site_name = site.display_name
                ctx.site_url = site.site_url
                ctx.protected_object_id = site.id
                ctx.synced_at = now
            else:
                ctx = SiteContext(
                    tenant_id=tenant.id,
                    protected_object_id=site.id,
                    ms_site_id=site.ms_object_id,
                    site_url=site.site_url,
                    site_name=site.display_name,
                    synced_at=now,
                )
                self.db.add(ctx)
            count += 1

        await self.db.flush()
        return count

    async def _link_protected_objects(self, tenant: Tenant):
        """Link UserContext records to their ProtectedObject records."""
        # Get all user contexts without a protected_object_id
        result = await self.db.execute(
            select(UserContext).where(
                UserContext.tenant_id == tenant.id,
                UserContext.protected_object_id.is_(None),
            )
        )
        unlinked = result.scalars().all()

        for ctx in unlinked:
            # Match by ms_object_id (Graph user ID)
            po_result = await self.db.execute(
                select(ProtectedObject).where(
                    ProtectedObject.tenant_id == tenant.id,
                    ProtectedObject.ms_object_id == ctx.ms_user_id,
                ).limit(1)
            )
            po = po_result.scalar_one_or_none()
            if po:
                ctx.protected_object_id = po.id

        await self.db.flush()
