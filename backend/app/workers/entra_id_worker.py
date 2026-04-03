"""Entra ID (Azure AD) backup worker.

Handles backup of Entra ID directory objects:
- Users (with delta query support for incremental backups)
- Groups + memberships (with delta query support)
- Directory roles + members
- Role assignments
- Conditional Access policies
- App registrations + service principals
- Named locations

All objects are stored as encrypted JSON blobs.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient, GraphAPIError
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.utils.retry import retry_async, record_failed_item
from app.workers.base_worker import BaseWorker, BackupItem

logger = logging.getLogger(__name__)

ITEM_MAX_RETRIES = 3
ITEM_BASE_DELAY = 2.0


class EntraIDWorker(BaseWorker):
    """Worker for Entra ID directory backup operations."""

    def workload_name(self) -> str:
        return "entra_id"

    async def discover_items(self, protected_object, delta_token=None):
        """Compatibility: Entra ID uses legacy backup() method directly."""
        return [], None

    async def backup(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> tuple[int, int, str]:
        """Backup Entra ID directory objects.

        Returns (item_count, total_size_bytes, new_delta_token).

        Delta token strategy: JSON dict with separate tokens for users and groups
        (the two object types that support delta queries). Other object types are
        always fully scanned — they are typically small (<100 items).
        """
        # Parse stored delta tokens
        tokens = {}
        if delta_token:
            try:
                tokens = json.loads(delta_token)
            except (json.JSONDecodeError, TypeError):
                tokens = {}

        new_tokens = {}

        # 1. Users (delta query supported)
        user_token = await self._backup_users(
            protected_object, snapshot, wrapped_dek,
            delta_token=tokens.get("users"),
        )
        if user_token:
            new_tokens["users"] = user_token

        # 2. Groups + members (delta query supported)
        group_token = await self._backup_groups(
            protected_object, snapshot, wrapped_dek,
            delta_token=tokens.get("groups"),
        )
        if group_token:
            new_tokens["groups"] = group_token

        # 3-12. Non-delta objects (always full scan — small sets)
        await self._backup_directory_roles(protected_object, snapshot, wrapped_dek)
        await self._backup_role_assignments(protected_object, snapshot, wrapped_dek)
        await self._backup_conditional_access(protected_object, snapshot, wrapped_dek)
        await self._backup_applications(protected_object, snapshot, wrapped_dek)
        await self._backup_named_locations(protected_object, snapshot, wrapped_dek)
        await self._backup_service_principals(protected_object, snapshot, wrapped_dek)
        await self._backup_administrative_units(protected_object, snapshot, wrapped_dek)
        await self._backup_oauth_grants(protected_object, snapshot, wrapped_dek)
        await self._backup_devices(protected_object, snapshot, wrapped_dek)
        await self._backup_domains(protected_object, snapshot, wrapped_dek)

        # Phase 3: PIM backup (Enterprise feature)
        await self._backup_pim_eligibility(protected_object, snapshot, wrapped_dek)
        await self._backup_pim_assignments(protected_object, snapshot, wrapped_dek)

        # Count totals
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        item_count = row[0] or 0
        total_size = row[1] or 0

        return item_count, total_size, json.dumps(new_tokens) if new_tokens else None

    # ── Helper: store a single Entra ID object ──

    @retry_async(max_retries=ITEM_MAX_RETRIES, base_delay=ITEM_BASE_DELAY)
    async def _store_item(
        self,
        obj: dict,
        item_type: ItemType,
        ms_item_id: str,
        name: str,
        path: str,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        metadata: dict = None,
    ):
        """Serialize, encrypt, and store a single Entra ID object."""
        obj_data = json.dumps(obj, default=str).encode("utf-8")

        result = await self.storage.store_item(
            tenant_id=protected_object.tenant_id,
            workload="entra_id",
            object_id=protected_object.ms_object_id,
            snapshot_id=snapshot.id,
            item_id=ms_item_id,
            data=obj_data,
            wrapped_dek=wrapped_dek,
            mime_type="application/json",
            db=self.db,
        )

        item = SnapshotItem(
            snapshot_id=snapshot.id,
            item_type=item_type,
            ms_item_id=ms_item_id,
            name=name,
            path=path,
            size_bytes=len(obj_data),
            compressed_size=result.compressed_size,
            content_hash=result.content_hash,
            storage_flags=result.storage_flags,
            blob_path=result.blob_path,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(item)

    # ── 1. Users ──

    async def _backup_users(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> str:
        """Backup users with delta query support."""
        select_fields = (
            "id,displayName,mail,userPrincipalName,jobTitle,department,"
            "officeLocation,mobilePhone,businessPhones,accountEnabled,"
            "createdDateTime,userType,assignedLicenses,assignedPlans"
        )

        try:
            if delta_token:
                users, new_delta = await self.graph.get_delta(
                    "/users/delta", delta_token=delta_token
                )
            else:
                # Initial full sync — use get_all_pages for reliability
                # (get_delta doesn't accept params for $select)
                users = await self.graph.get_all_pages(
                    "/users", params={"$select": select_fields, "$top": "999"}
                )
                new_delta = None  # Will get delta token on next incremental run

            count = 0
            for user in users:
                if user.get("@removed"):
                    continue  # Skip deleted users in delta response
                try:
                    await self._store_item(
                        obj=user,
                        item_type=ItemType.USER,
                        ms_item_id=user["id"],
                        name=user.get("displayName", "Unknown User"),
                        path="Users",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "userPrincipalName": user.get("userPrincipalName"),
                            "mail": user.get("mail"),
                            "accountEnabled": user.get("accountEnabled"),
                            "userType": user.get("userType"),
                            "department": user.get("department"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup user {user.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=user.get("id"), item_type_str="user",
                        item_name=user.get("displayName", "Unknown"), item_path="Users",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} users")
            return new_delta

        except Exception as e:
            logger.error(f"Failed to backup users: {e}")
            return None

    # ── 2. Groups ──

    async def _backup_groups(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> str:
        """Backup groups with memberships and delta query support."""
        try:
            if delta_token:
                groups, new_delta = await self.graph.get_delta(
                    "/groups/delta", delta_token=delta_token
                )
            else:
                # Initial full sync
                groups = await self.graph.get_all_pages(
                    "/groups",
                    params={"$select": "id,displayName,description,mail,groupTypes,securityEnabled,mailEnabled,membershipRule,membershipRuleProcessingState", "$top": "999"}
                )
                new_delta = None

            count = 0
            for group in groups:
                if group.get("@removed"):
                    continue
                try:
                    # Fetch group members
                    members = []
                    try:
                        members = await self.graph.get_all_pages(
                            f"/groups/{group['id']}/members",
                            params={"$select": "id,displayName,userPrincipalName", "$top": "999"},
                        )
                    except Exception as me:
                        logger.warning(f"Failed to get members for group {group['id']}: {me}")

                    group_with_members = {**group, "_members": members}

                    # Determine group type for metadata
                    group_types = group.get("groupTypes", [])
                    is_dynamic = "DynamicMembership" in group_types
                    is_m365 = "Unified" in group_types
                    group_kind = "dynamic" if is_dynamic else ("m365" if is_m365 else "security")

                    await self._store_item(
                        obj=group_with_members,
                        item_type=ItemType.GROUP,
                        ms_item_id=group["id"],
                        name=group.get("displayName", "Unknown Group"),
                        path="Groups",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "groupType": group_kind,
                            "securityEnabled": group.get("securityEnabled"),
                            "mailEnabled": group.get("mailEnabled"),
                            "memberCount": len(members),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup group {group.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=group.get("id"), item_type_str="group",
                        item_name=group.get("displayName", "Unknown"), item_path="Groups",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} groups")
            return new_delta

        except Exception as e:
            logger.error(f"Failed to backup groups: {e}")
            return None

    # ── 3. Directory Roles ──

    async def _backup_directory_roles(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup directory roles and their members (always full scan)."""
        try:
            roles = await self.graph.get_all_pages(
                "/directoryRoles",
                params={"$select": "id,displayName,description,roleTemplateId"},
            )
            count = 0
            for role in roles:
                try:
                    # Fetch role members
                    members = []
                    try:
                        members = await self.graph.get_all_pages(
                            f"/directoryRoles/{role['id']}/members",
                            params={"$select": "id,displayName,userPrincipalName"},
                        )
                    except Exception:
                        pass

                    role_with_members = {**role, "_members": members}

                    await self._store_item(
                        obj=role_with_members,
                        item_type=ItemType.DIRECTORY_ROLE,
                        ms_item_id=role["id"],
                        name=role.get("displayName", "Unknown Role"),
                        path="Directory Roles",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "roleTemplateId": role.get("roleTemplateId"),
                            "memberCount": len(members),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup role {role.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=role.get("id"), item_type_str="directory_role",
                        item_name=role.get("displayName", "Unknown"), item_path="Directory Roles",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} directory roles")

        except Exception as e:
            logger.error(f"Failed to backup directory roles: {e}")

    # ── 4. Role Assignments ──

    async def _backup_role_assignments(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup directory role assignments."""
        try:
            assignments = await self.graph.get_all_pages(
                "/roleManagement/directory/roleAssignments",
                params={"$expand": "principal($select=id,displayName)"},
            )
            count = 0
            for assignment in assignments:
                try:
                    principal = assignment.get("principal", {})
                    name = f"{principal.get('displayName', 'Unknown')} -> {assignment.get('roleDefinitionId', '')[:8]}"

                    await self._store_item(
                        obj=assignment,
                        item_type=ItemType.ROLE_ASSIGNMENT,
                        ms_item_id=assignment["id"],
                        name=name,
                        path="Role Assignments",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "principalId": assignment.get("principalId"),
                            "roleDefinitionId": assignment.get("roleDefinitionId"),
                            "directoryScopeId": assignment.get("directoryScopeId"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup role assignment {assignment.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=assignment.get("id"), item_type_str="role_assignment",
                        item_name=name, item_path="Role Assignments",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} role assignments")

        except Exception as e:
            logger.error(f"Failed to backup role assignments: {e}")

    # ── 5. Conditional Access Policies ──

    async def _backup_conditional_access(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup Conditional Access policies."""
        try:
            policies = await self.graph.get_all_pages(
                "/identity/conditionalAccess/policies",
            )
            count = 0
            for policy in policies:
                try:
                    await self._store_item(
                        obj=policy,
                        item_type=ItemType.CONDITIONAL_ACCESS_POLICY,
                        ms_item_id=policy["id"],
                        name=policy.get("displayName", "Unnamed Policy"),
                        path="Conditional Access",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "state": policy.get("state"),
                            "createdDateTime": policy.get("createdDateTime"),
                            "modifiedDateTime": policy.get("modifiedDateTime"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup CA policy {policy.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=policy.get("id"), item_type_str="conditional_access_policy",
                        item_name=policy.get("displayName", "Unknown"), item_path="Conditional Access",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} Conditional Access policies")

        except Exception as e:
            logger.error(f"Failed to backup Conditional Access policies: {e}")

    # ── 6. App Registrations ──

    async def _backup_applications(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup app registrations and service principals."""
        try:
            apps = await self.graph.get_all_pages(
                "/applications",
                params={"$select": "id,appId,displayName,signInAudience,api,web,requiredResourceAccess,keyCredentials,passwordCredentials,createdDateTime"},
            )
            count = 0
            for app in apps:
                try:
                    # Strip secret values from credentials for safety
                    sanitized_app = {**app}
                    if "passwordCredentials" in sanitized_app:
                        sanitized_app["passwordCredentials"] = [
                            {k: v for k, v in cred.items() if k != "secretText"}
                            for cred in sanitized_app.get("passwordCredentials", [])
                        ]

                    await self._store_item(
                        obj=sanitized_app,
                        item_type=ItemType.APP_REGISTRATION,
                        ms_item_id=app["id"],
                        name=app.get("displayName", "Unknown App"),
                        path="App Registrations",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "appId": app.get("appId"),
                            "signInAudience": app.get("signInAudience"),
                            "createdDateTime": app.get("createdDateTime"),
                            "hasCredentials": bool(app.get("keyCredentials") or app.get("passwordCredentials")),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup app {app.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=app.get("id"), item_type_str="app_registration",
                        item_name=app.get("displayName", "Unknown"), item_path="App Registrations",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} app registrations")

        except Exception as e:
            logger.error(f"Failed to backup applications: {e}")

    # ── 7. Named Locations ──

    async def _backup_named_locations(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup named locations used in Conditional Access."""
        try:
            locations = await self.graph.get_all_pages(
                "/identity/conditionalAccess/namedLocations",
            )
            count = 0
            for location in locations:
                try:
                    loc_type = location.get("@odata.type", "").split(".")[-1]

                    await self._store_item(
                        obj=location,
                        item_type=ItemType.NAMED_LOCATION,
                        ms_item_id=location["id"],
                        name=location.get("displayName", "Unknown Location"),
                        path="Named Locations",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "locationType": loc_type,
                            "isTrusted": location.get("isTrusted"),
                            "createdDateTime": location.get("createdDateTime"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup named location {location.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=location.get("id"), item_type_str="named_location",
                        item_name=location.get("displayName", "Unknown"), item_path="Named Locations",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} named locations")

        except Exception as e:
            logger.error(f"Failed to backup named locations: {e}")

    # ── 8. Service Principals (Enterprise Apps) ──

    async def _backup_service_principals(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup service principals (enterprise applications)."""
        try:
            sps = await self.graph.get_all_pages(
                "/servicePrincipals",
                params={"$select": "id,appId,displayName,servicePrincipalType,accountEnabled,appRoleAssignmentRequired,tags,loginUrl,logoutUrl,homepage,createdDateTime", "$top": "999"},
            )
            count = 0
            for sp in sps:
                try:
                    await self._store_item(
                        obj=sp,
                        item_type=ItemType.SERVICE_PRINCIPAL,
                        ms_item_id=sp["id"],
                        name=sp.get("displayName", "Unknown Service Principal"),
                        path="Service Principals",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "appId": sp.get("appId"),
                            "servicePrincipalType": sp.get("servicePrincipalType"),
                            "accountEnabled": sp.get("accountEnabled"),
                            "createdDateTime": sp.get("createdDateTime"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup service principal {sp.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=sp.get("id"), item_type_str="service_principal",
                        item_name=sp.get("displayName", "Unknown"), item_path="Service Principals",
                    )
            await self.db.flush()
            logger.info(f"Backed up {count} service principals")
        except Exception as e:
            logger.error(f"Failed to backup service principals: {e}")

    # ── 9. Administrative Units ──

    async def _backup_administrative_units(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup administrative units with members."""
        try:
            units = await self.graph.get_all_pages(
                "/directory/administrativeUnits",
                params={"$select": "id,displayName,description,membershipType,membershipRule,visibility"},
            )
            count = 0
            for unit in units:
                try:
                    members = []
                    try:
                        members = await self.graph.get_all_pages(
                            f"/directory/administrativeUnits/{unit['id']}/members",
                            params={"$select": "id,displayName"},
                        )
                    except Exception:
                        pass

                    unit_with_members = {**unit, "_members": members}
                    await self._store_item(
                        obj=unit_with_members,
                        item_type=ItemType.ADMINISTRATIVE_UNIT,
                        ms_item_id=unit["id"],
                        name=unit.get("displayName", "Unknown Admin Unit"),
                        path="Administrative Units",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "membershipType": unit.get("membershipType"),
                            "memberCount": len(members),
                            "visibility": unit.get("visibility"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup admin unit {unit.get('id')}: {e}")
            await self.db.flush()
            logger.info(f"Backed up {count} administrative units")
        except Exception as e:
            logger.error(f"Failed to backup administrative units: {e}")

    # ── 10. OAuth Permission Grants ──

    async def _backup_oauth_grants(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup OAuth2 permission grants (delegated permissions)."""
        try:
            grants = await self.graph.get_all_pages(
                "/oauth2PermissionGrants",
                params={"$top": "999"},
            )
            count = 0
            for grant in grants:
                try:
                    scope = grant.get("scope", "").strip()
                    name = f"{grant.get('clientId', '?')[:8]} → {scope[:50]}" if scope else f"Grant {grant.get('id', '?')[:8]}"

                    await self._store_item(
                        obj=grant,
                        item_type=ItemType.OAUTH_PERMISSION_GRANT,
                        ms_item_id=grant["id"],
                        name=name,
                        path="OAuth Permission Grants",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "clientId": grant.get("clientId"),
                            "resourceId": grant.get("resourceId"),
                            "scope": scope,
                            "consentType": grant.get("consentType"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup OAuth grant {grant.get('id')}: {e}")
            await self.db.flush()
            logger.info(f"Backed up {count} OAuth permission grants")
        except Exception as e:
            logger.error(f"Failed to backup OAuth grants: {e}")

    # ── 11. Devices ──

    async def _backup_devices(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup registered and joined devices."""
        try:
            devices = await self.graph.get_all_pages(
                "/devices",
                params={"$select": "id,displayName,deviceId,operatingSystem,operatingSystemVersion,trustType,accountEnabled,isManaged,isCompliant,registeredOwners,registeredUsers,createdDateTime", "$top": "999"},
            )
            count = 0
            for device in devices:
                try:
                    await self._store_item(
                        obj=device,
                        item_type=ItemType.DEVICE,
                        ms_item_id=device["id"],
                        name=device.get("displayName", "Unknown Device"),
                        path="Devices",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "operatingSystem": device.get("operatingSystem"),
                            "trustType": device.get("trustType"),
                            "accountEnabled": device.get("accountEnabled"),
                            "isManaged": device.get("isManaged"),
                            "isCompliant": device.get("isCompliant"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup device {device.get('id')}: {e}")
            await self.db.flush()
            logger.info(f"Backed up {count} devices")
        except Exception as e:
            logger.error(f"Failed to backup devices: {e}")

    # ── 12. Custom Domains ──

    async def _backup_domains(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup verified custom domains."""
        try:
            domains = await self.graph.get_all_pages(
                "/domains",
                params={"$select": "id,authenticationType,isDefault,isVerified,supportedServices"},
            )
            count = 0
            for domain in domains:
                try:
                    await self._store_item(
                        obj=domain,
                        item_type=ItemType.DOMAIN,
                        ms_item_id=domain["id"],
                        name=domain.get("id", "Unknown Domain"),
                        path="Domains",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "authenticationType": domain.get("authenticationType"),
                            "isDefault": domain.get("isDefault"),
                            "isVerified": domain.get("isVerified"),
                            "supportedServices": domain.get("supportedServices"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup domain {domain.get('id')}: {e}")
            await self.db.flush()
            logger.info(f"Backed up {count} domains")
        except Exception as e:
            logger.error(f"Failed to backup domains: {e}")

    # ── PIM Assignment Backup (Enterprise) ──

    async def _backup_pim_eligibility(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup PIM eligible role assignments. Enterprise-only feature."""
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("pim_backup"):
            return

        try:
            eligibilities = await self.graph.get_all_pages(
                "/roleManagement/directory/roleEligibilityScheduleInstances",
            )
            count = 0
            for elig in eligibilities:
                try:
                    await self._store_item(
                        obj=elig,
                        item_type=ItemType.PIM_ELIGIBILITY,
                        ms_item_id=elig.get("id", f"pim_elig_{count}"),
                        name=f"PIM Eligibility: {elig.get('principalId', 'unknown')} → {elig.get('roleDefinitionId', 'unknown')}",
                        path="PIM/Eligibility",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "principalId": elig.get("principalId"),
                            "roleDefinitionId": elig.get("roleDefinitionId"),
                            "directoryScopeId": elig.get("directoryScopeId"),
                            "startDateTime": elig.get("startDateTime"),
                            "endDateTime": elig.get("endDateTime"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup PIM eligibility: {e}")
            if count:
                await self.db.flush()
                logger.info(f"Backed up {count} PIM eligibility assignments")
        except Exception as e:
            logger.warning(f"PIM eligibility backup failed (may need RoleEligibilitySchedule.Read.Directory scope): {e}")

    async def _backup_pim_assignments(
        self, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup PIM active role assignments. Enterprise-only feature."""
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("pim_backup"):
            return

        try:
            assignments = await self.graph.get_all_pages(
                "/roleManagement/directory/roleAssignmentScheduleInstances",
            )
            count = 0
            for assgn in assignments:
                try:
                    await self._store_item(
                        obj=assgn,
                        item_type=ItemType.PIM_ASSIGNMENT,
                        ms_item_id=assgn.get("id", f"pim_assgn_{count}"),
                        name=f"PIM Assignment: {assgn.get('principalId', 'unknown')} → {assgn.get('roleDefinitionId', 'unknown')}",
                        path="PIM/Assignments",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "principalId": assgn.get("principalId"),
                            "roleDefinitionId": assgn.get("roleDefinitionId"),
                            "directoryScopeId": assgn.get("directoryScopeId"),
                            "assignmentType": assgn.get("assignmentType"),
                            "startDateTime": assgn.get("startDateTime"),
                            "endDateTime": assgn.get("endDateTime"),
                        },
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to backup PIM assignment: {e}")
            if count:
                await self.db.flush()
                logger.info(f"Backed up {count} PIM active assignments")
        except Exception as e:
            logger.warning(f"PIM assignment backup failed: {e}")

    # ── Restore Operations ──

    async def restore_items(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
        protected_object: ProtectedObject = None,
    ) -> int:
        """Restore Entra ID objects by recreating them via Graph API.

        Supports: Conditional Access policies, groups, app registrations, named locations.
        Users and directory roles are read-only (can't be created via API).
        """
        from sqlalchemy import select
        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()
        restored = 0

        for item in items:
            try:
                # Retrieve and decrypt the backed-up JSON
                data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                obj_data = json.loads(data)

                if item.item_type == ItemType.CONDITIONAL_ACCESS_POLICY:
                    await self._restore_ca_policy(obj_data)
                    restored += 1
                elif item.item_type == ItemType.GROUP:
                    await self._restore_group(obj_data)
                    restored += 1
                elif item.item_type == ItemType.APP_REGISTRATION:
                    await self._restore_app(obj_data)
                    restored += 1
                elif item.item_type == ItemType.NAMED_LOCATION:
                    await self._restore_named_location(obj_data)
                    restored += 1
                else:
                    logger.info(f"Skipping restore of {item.item_type.value} — read-only object type")

            except Exception as e:
                logger.error(f"Failed to restore {item.item_type.value} {item.ms_item_id}: {e}")

        return restored

    async def _restore_ca_policy(self, obj_data: dict):
        """Recreate a Conditional Access policy."""
        restore_body = {
            "displayName": f"[Restored] {obj_data.get('displayName', 'Unknown')}",
            "state": "disabled",  # Always restore as disabled for safety
            "conditions": obj_data.get("conditions", {}),
            "grantControls": obj_data.get("grantControls"),
            "sessionControls": obj_data.get("sessionControls"),
        }
        await self.graph.post("/identity/conditionalAccess/policies", json_data=restore_body)

    async def _restore_group(self, obj_data: dict):
        """Recreate a group with its members. Member restore gated to Business+."""
        restore_body = {
            "displayName": f"[Restored] {obj_data.get('displayName', 'Unknown')}",
            "description": obj_data.get("description"),
            "mailEnabled": obj_data.get("mailEnabled", False),
            "mailNickname": f"restored_{obj_data.get('mailNickname', 'group')}",
            "securityEnabled": obj_data.get("securityEnabled", True),
            "groupTypes": obj_data.get("groupTypes", []),
        }
        result = await self.graph.post("/groups", json_data=restore_body)
        new_group_id = result.get("id") if isinstance(result, dict) else None

        # Restore group members (Business+ feature)
        if new_group_id:
            from app.services.feature_flags import feature_flags
            members = obj_data.get("_members", [])
            if members and feature_flags.is_enabled("entra_member_restore"):
                restored_members = 0
                for member in members:
                    member_id = member.get("id")
                    if not member_id:
                        continue
                    try:
                        await self.graph.post(
                            f"/groups/{new_group_id}/members/$ref",
                            json_data={
                                "@odata.id": f"https://graph.microsoft.com/v1.0/directoryObjects/{member_id}"
                            },
                        )
                        restored_members += 1
                    except Exception as e:
                        logger.warning(f"Failed to add member {member_id} to group {new_group_id}: {e}")
                if restored_members:
                    logger.info(f"Restored {restored_members}/{len(members)} members to group {new_group_id}")

    async def _restore_app(self, obj_data: dict):
        """Recreate an app registration."""
        restore_body = {
            "displayName": f"[Restored] {obj_data.get('displayName', 'Unknown')}",
            "signInAudience": obj_data.get("signInAudience", "AzureADMyOrg"),
        }
        if obj_data.get("web"):
            restore_body["web"] = obj_data["web"]
        if obj_data.get("api"):
            restore_body["api"] = obj_data["api"]
        await self.graph.post("/applications", json_data=restore_body)

    async def _restore_named_location(self, obj_data: dict):
        """Recreate a named location."""
        odata_type = obj_data.get("@odata.type", "")
        restore_body = {
            "@odata.type": odata_type,
            "displayName": f"[Restored] {obj_data.get('displayName', 'Unknown')}",
        }
        if "ipNamedLocation" in odata_type:
            restore_body["ipRanges"] = obj_data.get("ipRanges", [])
            restore_body["isTrusted"] = obj_data.get("isTrusted", False)
        elif "countryNamedLocation" in odata_type:
            restore_body["countriesAndRegions"] = obj_data.get("countriesAndRegions", [])
        await self.graph.post("/identity/conditionalAccess/namedLocations", json_data=restore_body)
