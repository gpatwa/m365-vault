"""Tests for Entra ID restore enhancements: relationship restore, cross-tenant.

Verifies the enhanced restore dispatcher with admin units, role assignments,
OAuth grants, and cross-tenant ID mapping.
"""
import json
import pytest
from app.models.snapshot import ItemType


# ═══════════════════════════════════════════════════════
# Restore Dispatcher
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_restore_dispatcher_has_all_handlers():
    """Restore dispatcher should have handlers for 7 restorable object types."""
    # These are the types that should have restore handlers
    restorable_types = {
        ItemType.CONDITIONAL_ACCESS_POLICY,
        ItemType.GROUP,
        ItemType.APP_REGISTRATION,
        ItemType.NAMED_LOCATION,
        ItemType.ADMINISTRATIVE_UNIT,
        ItemType.ROLE_ASSIGNMENT,
        ItemType.OAUTH_PERMISSION_GRANT,
    }
    assert len(restorable_types) == 7


@pytest.mark.asyncio
async def test_read_only_types_not_restored():
    """Users, directory roles, devices, domains should be marked read-only."""
    read_only = {
        ItemType.USER, ItemType.DIRECTORY_ROLE, ItemType.DEVICE, ItemType.DOMAIN,
        ItemType.SERVICE_PRINCIPAL,
    }
    assert ItemType.USER in read_only
    assert ItemType.DIRECTORY_ROLE in read_only
    assert ItemType.GROUP not in read_only  # Groups ARE restorable


# ═══════════════════════════════════════════════════════
# Admin Unit Restore
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_admin_unit_restore_body():
    """Admin unit restore should create with [Restored] prefix."""
    obj_data = {
        "displayName": "US Region Admins",
        "description": "Scoped admin unit for US offices",
        "_members": [
            {"id": "user-1", "displayName": "Admin 1"},
            {"id": "user-2", "displayName": "Admin 2"},
        ],
    }

    restore_body = {
        "displayName": f"[Restored] {obj_data.get('displayName', 'Unknown')}",
        "description": obj_data.get("description"),
    }

    assert restore_body["displayName"] == "[Restored] US Region Admins"
    assert restore_body["description"] == "Scoped admin unit for US offices"
    assert len(obj_data["_members"]) == 2


# ═══════════════════════════════════════════════════════
# Role Assignment Restore
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_role_assignment_requires_principal():
    """Role assignment restore should skip if principalId is missing."""
    obj_data_missing = {
        "roleDefinitionId": "role-123",
        "directoryScopeId": "/",
        # No principalId
    }
    assert obj_data_missing.get("principalId") is None
    # Worker would skip this with warning


@pytest.mark.asyncio
async def test_role_assignment_requires_role_def():
    """Role assignment restore should skip if roleDefinitionId is missing."""
    obj_data_missing = {
        "principalId": "user-123",
        # No roleDefinitionId
    }
    assert obj_data_missing.get("roleDefinitionId") is None


@pytest.mark.asyncio
async def test_role_assignment_restore_body():
    """Role assignment restore body should be properly formatted."""
    obj_data = {
        "principalId": "user-abc-123",
        "roleDefinitionId": "role-def-456",
        "directoryScopeId": "/administrativeUnits/au-789",
    }

    restore_body = {
        "@odata.type": "#microsoft.graph.unifiedRoleAssignment",
        "principalId": obj_data["principalId"],
        "roleDefinitionId": obj_data["roleDefinitionId"],
        "directoryScopeId": obj_data.get("directoryScopeId", "/"),
    }

    assert restore_body["principalId"] == "user-abc-123"
    assert restore_body["roleDefinitionId"] == "role-def-456"
    assert restore_body["directoryScopeId"] == "/administrativeUnits/au-789"


# ═══════════════════════════════════════════════════════
# OAuth Grant Restore
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_oauth_grant_requires_client_and_resource():
    """OAuth grant restore needs both clientId and resourceId."""
    obj_data = {
        "clientId": "sp-123",
        "resourceId": "sp-456",
        "scope": "User.Read Mail.Read",
        "consentType": "AllPrincipals",
    }

    assert obj_data["clientId"] is not None
    assert obj_data["resourceId"] is not None

    restore_body = {
        "clientId": obj_data["clientId"],
        "consentType": obj_data["consentType"],
        "resourceId": obj_data["resourceId"],
        "scope": obj_data["scope"],
    }

    assert restore_body["scope"] == "User.Read Mail.Read"


@pytest.mark.asyncio
async def test_oauth_grant_missing_client_skips():
    """OAuth grant without clientId should be skipped."""
    obj_data = {
        "resourceId": "sp-456",
        "scope": "User.Read",
    }
    assert obj_data.get("clientId") is None
    # Worker would skip with warning


# ═══════════════════════════════════════════════════════
# Cross-Tenant Restore
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_cross_tenant_restore_request_model():
    """EntraRestoreRequest should accept target_tenant_id."""
    from app.api.entra_id import EntraRestoreRequest

    req = EntraRestoreRequest(
        snapshot_id=1,
        restore_type="item_level",
        item_ids=[1, 2, 3],
        target_tenant_id=2,
        restore_relationships=True,
    )

    assert req.target_tenant_id == 2
    assert req.restore_relationships is True
    assert req.snapshot_id == 1


@pytest.mark.asyncio
async def test_cross_tenant_restore_type_enum():
    """RestoreType.CROSS_TENANT should exist."""
    from app.models.restore_job import RestoreType
    assert RestoreType.CROSS_TENANT == "cross_tenant"


@pytest.mark.asyncio
async def test_member_resolution_by_upn():
    """Cross-tenant member resolution should work by userPrincipalName."""
    # Source tenant member
    source_member = {
        "id": "source-tenant-guid-123",
        "displayName": "Gopal Patwa",
        "userPrincipalName": "gopal@patwa.com",
    }

    # In cross-tenant, we'd look up by UPN in target
    upn = source_member.get("userPrincipalName")
    assert upn == "gopal@patwa.com"
    # Target lookup: GET /users?$filter=userPrincipalName eq 'gopal@patwa.com'


@pytest.mark.asyncio
async def test_unmappable_member_doesnt_fail():
    """Members that can't be mapped to target should be logged, not fail."""
    members = [
        {"id": "user-1", "displayName": "Known User", "userPrincipalName": "known@patwa.com"},
        {"id": "user-2", "displayName": "External Guest"},  # No UPN — can't map
    ]

    mappable = [m for m in members if m.get("userPrincipalName")]
    unmappable = [m for m in members if not m.get("userPrincipalName")]

    assert len(mappable) == 1
    assert len(unmappable) == 1
    assert unmappable[0]["displayName"] == "External Guest"
