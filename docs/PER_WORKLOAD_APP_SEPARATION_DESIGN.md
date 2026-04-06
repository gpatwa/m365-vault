# Per-Workload Entra ID App Separation Architecture

**Status:** Design v2 (Updated 2026-04-06)
**Date:** 2026-04-04 (created), 2026-04-06 (revised)
**Author:** KavachIQ Engineering
**Affects:** Backend, Frontend, Onboarding, Graph Client, Provisioning

---

## 1. Problem Statement

Today, each KavachIQ tenant has a **single Entra ID app registration** (`tenants.client_id` / `tenants.client_secret_encrypted`) with all Graph API permissions for every workload. This creates three problems:

1. **Over-permissioned:** A customer who only backs up Exchange still grants Directory.Read.All, Sites.Read.All, Files.Read.All, Chat.Read.All, etc.
2. **Blast radius:** If the single app secret leaks, the attacker has read/write access to *all* M365 workloads.
3. **Compliance friction:** Security-conscious customers (financial, healthcare, government) refuse to grant "all permissions upfront" and delay onboarding.

### Decision Record (Updated 2026-04-06)

- Per-workload separation is the primary axis — each workload gets its own multi-tenant app.
- **SaaS model (default):** Apps live in KavachIQ's Entra tenant. KavachIQ manages secrets.
  Customers consent per-workload — only the workloads they need.
- **Self-hosted model (enterprise):** Bootstrap pattern creates apps in customer's tenant.
  Customer manages secrets via their own Key Vault / Managed Identity.
- **Restore permissions:** Delegated consent flow (no standing write access). Not per-app.
- **Throttling:** Per-workload apps are NOT for throttling (Microsoft blocks multi-app
  throttling workaround since March 2026). They're for security isolation ONLY.
- **Customer choice:** Customer picks which workloads to protect during onboarding.
  Only Exchange? Only Entra ID? Exchange + SharePoint? Their choice → only those
  apps get consented. No unnecessary permissions.

### Microsoft 365 Backup Storage API (Future)

The industry is moving to Microsoft's first-party Backup Storage API (no throttling,
fast restore). KavachIQ will adopt this as a secondary path while keeping Graph API
for air-gap copies and workloads Backup Storage doesn't support (Teams, Entra ID).

---

## 2. Target Architecture

```
Tenant: Contoso (ms_tenant_id = abc-123)
  |
  +-- KavachIQ-EntraID     (client_id_1)  -->  Directory.Read.All, User.Read/ReadWrite.All, Group.Read/ReadWrite.All, ...
  +-- KavachIQ-Exchange     (client_id_2)  -->  Mail.Read/ReadWrite, Calendars.Read/ReadWrite, Contacts.Read/ReadWrite
  +-- KavachIQ-SharePoint   (client_id_3)  -->  Sites.Selected (per-site grants)
  +-- KavachIQ-OneDrive     (client_id_4)  -->  Files.Read.All / Files.ReadWrite.All
  +-- KavachIQ-Teams        (client_id_5)  -->  Chat.Read.All, ChannelMessage.Read.All, Team.ReadBasic.All
```

Customer enables only the workloads they use. Each workload app has its own client_id, client_secret, consent status, and permission set.

---

## 3. Permissions Per Workload App

### 3.1 Entra ID App (`KavachIQ-EntraID`)

| Permission | Type | Purpose | Backup | Restore |
|---|---|---|---|---|
| Directory.Read.All | Application | Read directory objects | Y | Y |
| User.Read.All | Application | Read user profiles | Y | Y |
| User.ReadWrite.All | Application | Restore/create users | - | Y |
| Group.Read.All | Application | Read groups + membership | Y | Y |
| Group.ReadWrite.All | Application | Restore/create groups | - | Y |
| Application.ReadWrite.All | Application | Backup/restore app registrations | - | Y |
| RoleManagement.ReadWrite.Directory | Application | Backup/restore directory roles | - | Y |
| Policy.ReadWrite.ConditionalAccess | Application | Backup/restore CA policies | - | Y |
| Organization.Read.All | Application | Read org metadata | Y | Y |

### 3.2 Exchange App (`KavachIQ-Exchange`)

| Permission | Type | Purpose | Backup | Restore |
|---|---|---|---|---|
| Mail.Read | Application | Read mailbox messages | Y | - |
| Mail.ReadWrite | Application | Restore messages | - | Y |
| Calendars.Read | Application | Read calendar events | Y | - |
| Calendars.ReadWrite | Application | Restore calendar events | - | Y |
| Contacts.Read | Application | Read contacts | Y | - |
| Contacts.ReadWrite | Application | Restore contacts | - | Y |
| User.Read.All | Application | Enumerate mailboxes for discovery | Y | Y |

**Microsoft-specific: Exchange RBAC for Applications**

Exchange supports Application Access Policies (legacy) and the newer RBAC for Applications model. With RBAC for Apps, the Entra app can be scoped to specific mailboxes instead of `Mail.Read` on all mailboxes. This is valuable for:
- MSPs managing shared tenants
- Customers who want backup scoped to specific departments

Implementation:
1. After admin consent, use `New-ApplicationAccessPolicy` or RBAC for Apps cmdlet to scope the Exchange app to a distribution group
2. Store the scoping configuration in `tenant_workload_apps.config_json`
3. Discovery respects the scope -- only discovers mailboxes within the policy

### 3.3 SharePoint App (`KavachIQ-SharePoint`)

| Permission | Type | Purpose | Backup | Restore |
|---|---|---|---|---|
| Sites.Selected | Application | Read/write specific sites only | Y | Y |
| User.Read.All | Application | Resolve site ownership | Y | - |

**Microsoft-specific: Sites.Selected**

`Sites.Selected` is the Microsoft-recommended approach replacing `Sites.Read.All` / `Sites.ReadWrite.All`. Key differences:

- Does NOT appear in admin consent -- there is nothing to consent to globally
- After app registration, admin must grant per-site access via Graph API or SharePoint Admin Center
- Each site gets an explicit `read` or `write` permission grant

Onboarding flow for SharePoint:
1. Create app with `Sites.Selected` permission
2. Admin consents the app (grants the `Sites.Selected` scope)
3. KavachIQ calls `POST /sites/{site-id}/permissions` to request access to each site
4. Admin approves site-level access in SharePoint Admin Center (or via Graph API with Sites.FullControl.All on a provisioning app)
5. Store granted site IDs in `tenant_workload_apps.config_json.granted_sites[]`

API call to grant site permission:
```
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
{
  "roles": ["write"],
  "grantedToIdentities": [{
    "application": {
      "id": "<KavachIQ-SharePoint app client_id>",
      "displayName": "KavachIQ-SharePoint"
    }
  }]
}
```

### 3.4 OneDrive App (`KavachIQ-OneDrive`)

| Permission | Type | Purpose | Backup | Restore |
|---|---|---|---|---|
| Files.Read.All | Application | Read all user drives | Y | - |
| Files.ReadWrite.All | Application | Restore files to user drives | - | Y |
| User.Read.All | Application | Enumerate OneDrive users | Y | Y |

**Note:** Microsoft does not currently support `Files.Selected` for OneDrive (only SharePoint). `Files.Read.All` is the narrowest scope available. If Microsoft ships per-drive scoping in the future, we adopt it.

### 3.5 Teams App (`KavachIQ-Teams`)

| Permission | Type | Purpose | Backup | Restore |
|---|---|---|---|---|
| Chat.Read.All | Application | Read 1:1 and group chats | Y | - |
| ChannelMessage.Read.All | Application | Read channel messages | Y | - |
| Team.ReadBasic.All | Application | Enumerate teams | Y | - |
| TeamSettings.Read.All | Application | Read team settings | Y | - |
| Group.Read.All | Application | Read team membership | Y | - |
| Chat.ReadWrite.All | Application | Restore chat messages | - | Y |
| ChannelMessage.Send | Application | Restore channel messages | - | Y |

**Microsoft-specific: Resource-Specific Consent (RSC)**

Teams supports RSC where permissions are granted per-team instead of tenant-wide. This is opt-in and requires:
1. Teams admin enables RSC in Teams Admin Center
2. Team owner installs the KavachIQ Teams app in their team
3. The app receives scoped access to that team's channels and messages

RSC is a future enhancement. Phase 1 uses tenant-wide Teams permissions.

---

## 4. Data Model

### 4.1 New Table: `tenant_workload_apps`

**Recommendation: Option A (dedicated table)** -- Not a JSON column on the tenant model.

Rationale: Each workload app has its own credentials, consent lifecycle, status transitions, and audit trail. A relational table provides proper indexing, foreign keys, and migration safety.

```sql
CREATE TABLE tenant_workload_apps (
    id              SERIAL PRIMARY KEY,
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    workload        VARCHAR(30) NOT NULL,   -- entra_id, exchange, sharepoint, onedrive, teams

    -- Entra App Registration
    client_id       VARCHAR(255) NOT NULL,
    client_secret_encrypted TEXT NOT NULL,   -- AES-256 encrypted via encryption_service
    app_object_id   VARCHAR(255),           -- Entra object ID (for managing the app)
    sp_object_id    VARCHAR(255),           -- Service Principal object ID (for checking grants)

    -- Consent Status
    consent_status  VARCHAR(20) NOT NULL DEFAULT 'pending',
        -- pending:     app created, admin has not consented yet
        -- consented:   admin granted consent, permissions active
        -- partial:     some permissions granted (e.g., backup only, not restore)
        -- revoked:     admin revoked consent
        -- error:       consent flow failed

    -- Permission Tracking
    permissions_requested  TEXT,     -- JSON array: ["Mail.Read", "Mail.ReadWrite", ...]
    permissions_granted    TEXT,     -- JSON array: actually consented permissions
    backup_ready           BOOLEAN DEFAULT FALSE,
    restore_ready          BOOLEAN DEFAULT FALSE,

    -- Workload-specific Configuration
    config_json     TEXT,           -- JSON: workload-specific settings
        -- SharePoint: {"granted_sites": ["site-id-1", "site-id-2"], "site_permission_level": "write"}
        -- Exchange: {"scoped_to_group": "dept-finance@contoso.com", "rbac_policy_id": "..."}
        -- OneDrive: {} (no per-drive scoping yet)
        -- Teams: {"rsc_enabled": false, "rsc_teams": []}

    -- Secret Lifecycle
    secret_expires_at      TIMESTAMP,       -- When the client secret expires
    secret_rotation_warned BOOLEAN DEFAULT FALSE,

    -- Metadata
    enabled         BOOLEAN DEFAULT TRUE,   -- Admin can disable a workload without deleting
    last_used_at    TIMESTAMP,              -- Last time this app was used for API calls
    error_message   TEXT,                   -- Last error (e.g., "Token expired", "Consent revoked")
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),

    -- Constraints
    UNIQUE (tenant_id, workload)
);

CREATE INDEX idx_twa_tenant     ON tenant_workload_apps(tenant_id);
CREATE INDEX idx_twa_workload   ON tenant_workload_apps(workload);
CREATE INDEX idx_twa_status     ON tenant_workload_apps(consent_status);
CREATE INDEX idx_twa_secret_exp ON tenant_workload_apps(secret_expires_at);
```

### 4.2 SQLAlchemy Model

```python
# backend/app/models/tenant_workload_app.py

class ConsentStatus(str, enum.Enum):
    PENDING = "pending"
    CONSENTED = "consented"
    PARTIAL = "partial"
    REVOKED = "revoked"
    ERROR = "error"

class TenantWorkloadApp(Base):
    __tablename__ = "tenant_workload_apps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    workload = Column(String(30), nullable=False)  # entra_id, exchange, sharepoint, onedrive, teams

    client_id = Column(String(255), nullable=False)
    client_secret_encrypted = Column(Text, nullable=False)
    app_object_id = Column(String(255))
    sp_object_id = Column(String(255))

    consent_status = Column(Enum(ConsentStatus), default=ConsentStatus.PENDING)
    permissions_requested = Column(Text)   # JSON
    permissions_granted = Column(Text)     # JSON
    backup_ready = Column(Boolean, default=False)
    restore_ready = Column(Boolean, default=False)

    config_json = Column(Text)             # JSON

    secret_expires_at = Column(DateTime)
    secret_rotation_warned = Column(Boolean, default=False)

    enabled = Column(Boolean, default=True)
    last_used_at = Column(DateTime)
    error_message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "workload", name="uq_tenant_workload"),
    )
```

### 4.3 Existing `tenants` Table -- No Schema Change

The existing `tenants.client_id` / `tenants.client_secret_encrypted` columns are preserved for backward compatibility (legacy single-app tenants). No columns added or removed.

---

## 5. Credential Resolution Logic

The core question: when BackupEngine / RestoreEngine / DiscoveryService needs a Graph client, how does it pick the right credentials?

### 5.1 Resolution Function

```python
# backend/app/services/credential_resolver.py

async def get_graph_client(
    db: AsyncSession,
    tenant: Tenant,
    workload: str,                               # "exchange", "entra_id", etc.
    access_mode: Literal["backup", "restore", "default"] = "default",
) -> GraphClient:
    """Resolve the correct Entra app credentials for a workload.

    Resolution order:
    1. Look up tenant_workload_apps for (tenant_id, workload) where enabled=True
    2. If found and consent_status='consented': use workload-specific credentials
    3. Else: fall back to tenant.client_id / tenant.client_secret_encrypted (legacy)
    """
    # Try workload-specific app first
    result = await db.execute(
        select(TenantWorkloadApp).where(
            TenantWorkloadApp.tenant_id == tenant.id,
            TenantWorkloadApp.workload == workload,
            TenantWorkloadApp.enabled == True,
        )
    )
    workload_app = result.scalar_one_or_none()

    if workload_app and workload_app.consent_status == ConsentStatus.CONSENTED:
        client_secret = encryption_service.decrypt_string(workload_app.client_secret_encrypted)
        # Update last_used_at
        workload_app.last_used_at = datetime.utcnow()
        await db.commit()
        return GraphClient(
            tenant_id=tenant.ms_tenant_id,
            client_id=workload_app.client_id,
            client_secret=client_secret,
            access_mode=access_mode,
        )

    # Fallback: legacy single-app credentials
    client_secret = encryption_service.decrypt_string(tenant.client_secret_encrypted)
    return GraphClient(
        tenant_id=tenant.ms_tenant_id,
        client_id=tenant.client_id,
        client_secret=client_secret,
        access_mode=access_mode,
    )
```

### 5.2 Where to Integrate

Current code that creates GraphClient instances (all use `tenant.client_id`):

| File | Method | Change |
|---|---|---|
| `backend/app/services/discovery.py` | `_get_graph_client()` | Pass workload to `get_graph_client()` -- discovery iterates workloads, so it calls once per workload |
| `backend/app/services/backup_engine.py` | `_get_graph_client()` | Resolve via `get_graph_client(tenant, obj.workload_type.value, "backup")` |
| `backend/app/services/restore_engine.py` | `_get_graph_client()` | Resolve via `get_graph_client(tenant, obj.workload_type.value, "restore")` |
| `backend/app/api/tenants.py` | `test_connection()` | Test each workload app separately |
| `backend/app/api/tenants.py` | `check_permissions()` | Check permissions per workload app |

---

## 6. Onboarding Flow

### 6.1 New Tenant (Per-Workload)

```
Step 1: Tenant Registration
  - Admin enters tenant name + MS tenant ID
  - Chooses workloads to protect: [x] Entra ID  [x] Exchange  [ ] SharePoint  [ ] OneDrive  [ ] Teams

Step 2: App Creation (per selected workload)
  - KavachIQ creates N app registrations in the customer's tenant
  - Each app is named: "KavachIQ-{WorkloadName}" (e.g., "KavachIQ-Exchange")
  - Each app requests only the permissions for that workload
  - Client secrets are generated and encrypted

Step 3: Admin Consent (per workload)
  - UI shows N consent buttons (one per workload)
  - Each button opens a separate Microsoft admin consent URL
  - Admin can consent workloads independently (e.g., consent Exchange now, SharePoint later)
  - Consent status tracked in tenant_workload_apps.consent_status

Step 4: Permission Verification
  - After consent, KavachIQ checks granted permissions per app
  - Updates backup_ready / restore_ready flags
  - UI shows per-workload status: "Exchange: Backup Ready, Restore Ready"

Step 5: Discovery
  - Only runs for consented workloads
  - Each workload discovery uses its own app credentials
```

### 6.2 API Endpoints

```
POST /api/tenants/                           -- Create tenant (unchanged)
POST /api/tenants/{id}/workloads             -- Enable workloads for a tenant
  Body: { "workloads": ["entra_id", "exchange"] }
  Response: { "apps_created": 2, "consent_urls": { "entra_id": "https://...", "exchange": "https://..." } }

GET  /api/tenants/{id}/workloads             -- List workload apps + status
  Response: [
    { "workload": "entra_id", "consent_status": "consented", "backup_ready": true, "restore_ready": true },
    { "workload": "exchange", "consent_status": "pending", "backup_ready": false, "restore_ready": false },
  ]

POST /api/tenants/{id}/workloads/{workload}/consent-url   -- Get consent URL for a specific workload
  Response: { "consent_url": "https://login.microsoftonline.com/..." }

POST /api/tenants/{id}/workloads/{workload}/check-consent -- Verify consent + update status
  Response: { "consent_status": "consented", "permissions_granted": [...], "backup_ready": true }

POST /api/tenants/{id}/workloads/{workload}/disable       -- Disable a workload (keep app, stop backups)
DELETE /api/tenants/{id}/workloads/{workload}              -- Remove workload app entirely

POST /api/tenants/{id}/workloads/sharepoint/grant-site     -- SharePoint: grant site access
  Body: { "site_id": "contoso.sharepoint.com,abc,def" }

GET  /api/tenants/{id}/workloads/sharepoint/sites          -- SharePoint: list granted sites
```

---

## 7. Frontend Changes

### 7.1 Onboarding Wizard

Replace the current single-app onboarding with a multi-step workload selector:

1. **Workload Selection** -- Checkbox grid of available workloads with descriptions
2. **App Creation** -- Progress indicator showing each app being created
3. **Consent** -- Per-workload consent buttons. Each opens a popup/redirect to Microsoft consent. Status updates in real-time.
4. **Verification** -- Green/red per-workload status. "Retry consent" for failed workloads.

### 7.2 Settings Page

Add a "Workloads" tab to the tenant settings:

- Table showing each workload app with: workload name, consent status, backup/restore readiness, secret expiry, last used
- Actions: Enable/Disable, Re-consent, Rotate Secret, Remove
- SharePoint section shows granted sites with add/remove

### 7.3 Permission Check Dialog

Current `check_permissions()` returns a flat result. Change to per-workload breakdown:

```json
{
  "workloads": {
    "entra_id": { "app_type": "per_workload", "backup_ready": true, "restore_ready": true },
    "exchange": { "app_type": "per_workload", "backup_ready": true, "restore_ready": false, "missing": ["Mail.ReadWrite"] },
    "sharepoint": { "app_type": "not_configured" }
  },
  "legacy_app": null
}
```

---

## 8. Migration Strategy

### 8.1 Backward Compatibility

Legacy tenants (created before per-workload) have:
- `tenants.client_id` + `tenants.client_secret_encrypted` (single app)
- No rows in `tenant_workload_apps`

The credential resolver falls back to `tenants.client_id` when no workload-specific app exists. This means:

- **Zero breaking changes** for existing tenants
- Legacy tenants continue working exactly as today
- No forced migration

### 8.2 Migration Path (Legacy to Per-Workload)

For existing tenants that want to adopt per-workload:

```
Step 1: Admin clicks "Upgrade to Per-Workload Apps" in Settings
Step 2: KavachIQ creates workload-specific apps for each active workload
Step 3: Admin consents each workload app
Step 4: KavachIQ verifies all consented apps have at least the same permissions as the legacy app
Step 5: KavachIQ switches credential resolution to per-workload
Step 6: Legacy app can be decommissioned (optional -- admin does this in Entra portal)
```

API endpoint:
```
POST /api/tenants/{id}/migrate-to-per-workload
  Response: { "apps_created": 3, "consent_urls": { ... }, "legacy_app_status": "will_be_fallback" }
```

### 8.3 Phased Rollout

| Phase | Scope | Duration |
|---|---|---|
| Phase 1 | New tenants get per-workload by default. Legacy tenants unchanged. | Weeks 1-4 |
| Phase 2 | UI nudge for legacy tenants to upgrade. Migration endpoint available. | Weeks 5-8 |
| Phase 3 | All new backup jobs use per-workload credentials (even for legacy, if available). | Weeks 9-12 |
| Phase 4 | Deprecation warning for legacy single-app. | Month 4+ |

---

## 9. Secret Rotation and Lifecycle

Each workload app has its own client secret with an expiration date. The system must:

1. **Track expiry:** `tenant_workload_apps.secret_expires_at`
2. **Warn ahead:** 30 days before expiry, set `secret_rotation_warned=True` and send alert
3. **Auto-rotate (optional):** If the provisioning app has `Application.ReadWrite.All`, create a new secret, update the encrypted value, delete the old secret
4. **Alert on failure:** If a workload app's token acquisition fails, update `consent_status='error'` and `error_message`

Cron job (daily):
```python
async def check_secret_expiry():
    """Alert on workload apps with secrets expiring within 30 days."""
    threshold = datetime.utcnow() + timedelta(days=30)
    expiring = await db.execute(
        select(TenantWorkloadApp).where(
            TenantWorkloadApp.secret_expires_at < threshold,
            TenantWorkloadApp.secret_rotation_warned == False,
            TenantWorkloadApp.enabled == True,
        )
    )
    for app in expiring.scalars():
        # Send alert, set warned flag
        ...
```

---

## 10. Graph API Metrics Update

The existing `GraphAPIMetrics` singleton classifies requests by workload via URL path matching. With per-workload apps, we gain a more reliable signal: the `client_id` itself identifies the workload.

Change: Add `client_id` to `GraphAPIMetrics.record()` and use it as a primary workload classifier, with path-based classification as fallback.

---

## 11. Competitive Positioning

### 11.1 How Competitors Handle This

| Vendor | App Model | Permissions | Per-Workload | Sites.Selected |
|---|---|---|---|---|
| **Veeam VBO** | Single app | All permissions upfront | No | No (Sites.Read.All) |
| **Rubrik Polaris** | Single app | All permissions upfront | No | No |
| **Druva inSync** | Single app | All permissions upfront | No | No |
| **Afi.ai** | Single app | All permissions upfront | No | No |
| **KavachIQ** (proposed) | Per-workload apps | Least-privilege per workload | **Yes** | **Yes** |

### 11.2 Differentiation Messaging

- **"Grant only what you use"** -- Customer backing up only Exchange sees only Exchange permissions in the consent dialog. No SharePoint, no Teams, no OneDrive permissions requested.
- **"Blast radius isolation"** -- If an Exchange app secret is compromised, the attacker cannot read SharePoint sites or OneDrive files.
- **"Sites.Selected support"** -- The only backup product that uses Microsoft's recommended per-site permission model instead of Sites.Read.All.
- **"Compliance-first"** -- Enables Zero Trust architecture for backup: each workload has its own identity, its own credentials, its own audit trail.
- **"Add workloads when ready"** -- Start with Exchange backup today, add SharePoint next quarter, add Teams when ready. No re-consent of a monolithic app.

### 11.3 Sales Motion

For security-conscious buyers (CISO, IT Security):
> "Unlike Veeam and Rubrik, KavachIQ doesn't require a single app with access to your entire M365 environment. Each workload gets its own isolated Entra app with only the permissions it needs. You consent Exchange permissions for Exchange backup, and that's all that app can see."

For compliance buyers:
> "KavachIQ is the only M365 backup solution that supports Microsoft's recommended Sites.Selected permission model for SharePoint. Your SharePoint backup app can only access the specific sites you approve -- not every site in the tenant."

---

## 12. Effort Estimate

| Work Item | Effort | Depends On |
|---|---|---|
| **Data model + migration SQL** | 2 days | - |
| SQLAlchemy model (`TenantWorkloadApp`) | 1 day | Data model |
| **Credential resolver service** | 2 days | Model |
| Update DiscoveryService | 1 day | Resolver |
| Update BackupEngine | 1 day | Resolver |
| Update RestoreEngine | 1 day | Resolver |
| **App provisioning (per-workload)** | 3 days | Model |
| Per-workload permission definitions | 1 day | Provisioning |
| Per-workload consent URL generation | 1 day | Provisioning |
| Consent callback + status tracking | 2 days | Provisioning |
| **API endpoints (workloads CRUD)** | 3 days | Model + Provisioning |
| SharePoint Sites.Selected grant flow | 2 days | API |
| **Frontend: onboarding wizard** | 4 days | API |
| Frontend: settings workloads tab | 3 days | API |
| Frontend: permission check per-workload | 2 days | API |
| **Secret rotation + alerting** | 2 days | Model |
| **Migration endpoint (legacy to per-workload)** | 2 days | Resolver + API |
| **Tests** | 3 days | All |
| **Documentation** | 1 day | All |
| **Total** | **~34 days** | (~7 weeks for 1 developer) |

### Priority Order

1. Data model + resolver + fallback (ensures zero regression for existing tenants)
2. API endpoints + provisioning
3. Frontend onboarding wizard
4. SharePoint Sites.Selected flow
5. Migration endpoint
6. Secret rotation
7. Exchange RBAC for Apps scoping
8. Teams RSC (future)

---

## 13. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Admin fatigue: N consent dialogs instead of 1 | Onboarding friction | Start with 2 (Entra + Exchange, the priority workloads). Others added later. Consent is async -- admin can do them in any order. |
| Sites.Selected complexity | SharePoint onboarding is slower | Provide a "grant all sites" convenience button that iterates sites and grants access. Fall back to Sites.Read.All as an option for less security-conscious customers. |
| Secret management: 5x more secrets to track | Operational overhead | Automated secret rotation + expiry alerting. Dashboard shows all secrets in one view. |
| Microsoft API rate limits: 5 apps per tenant hit separate quotas | Could be a benefit or risk | Benefit: each app has its own throttling budget. Risk: more token acquisitions. Mitigate with MSAL token caching per app. |
| Customer has existing Entra app they want to reuse | Breaks our provisioning model | Support "bring your own app" flow: customer provides client_id, we map it to a workload. |

---

## 14. Open Questions

1. **App naming convention:** `KavachIQ-Exchange` or `KavachIQ Backup - Exchange`? Need to be consistent and recognizable in customer's Entra portal.
2. **Multi-tenant provisioning app:** Should the provisioning app (that creates per-workload apps) be a single multi-tenant app, or do we use the customer's delegated token? Current code uses delegated token -- this scales.
3. **Exchange RBAC for Apps timeline:** This is a newer Microsoft feature. Do we implement Application Access Policies (legacy) first and add RBAC for Apps later, or wait for RBAC for Apps only?
4. **OneDrive per-user scoping:** Microsoft may ship `Files.Selected` or similar. Should we design the data model to accommodate this now?
5. **Teams protected API access:** `Chat.Read.All` and `ChannelMessage.Read.All` require a model=A license and Microsoft approval for protected APIs. Do we gate Teams workload behind a license check?

---

## 15. Appendix: Permission ID Reference

All permission IDs are for Microsoft Graph (`resourceAppId: 00000003-0000-0000-c000-000000000000`). IDs may vary -- the system should dynamically resolve role IDs from the Graph API `servicePrincipals` endpoint (as `check_granted_permissions()` already does today) rather than hardcoding them.

The `REQUIRED_APP_PERMISSIONS` dict in `app_provisioning.py` will be refactored from a flat dict into a per-workload structure:

```python
WORKLOAD_PERMISSIONS = {
    "entra_id": {
        "backup": ["Directory.Read.All", "User.Read.All", "Group.Read.All", "Organization.Read.All"],
        "restore": ["User.ReadWrite.All", "Group.ReadWrite.All", "Application.ReadWrite.All",
                     "RoleManagement.ReadWrite.Directory", "Policy.ReadWrite.ConditionalAccess"],
    },
    "exchange": {
        "backup": ["Mail.Read", "Calendars.Read", "Contacts.Read", "User.Read.All"],
        "restore": ["Mail.ReadWrite", "Calendars.ReadWrite", "Contacts.ReadWrite"],
    },
    "sharepoint": {
        "backup": ["Sites.Selected", "User.Read.All"],
        "restore": ["Sites.Selected"],   # Same permission, write granted per-site
    },
    "onedrive": {
        "backup": ["Files.Read.All", "User.Read.All"],
        "restore": ["Files.ReadWrite.All"],
    },
    "teams": {
        "backup": ["Chat.Read.All", "ChannelMessage.Read.All", "Team.ReadBasic.All",
                    "TeamSettings.Read.All", "Group.Read.All"],
        "restore": ["Chat.ReadWrite.All", "ChannelMessage.Send"],
    },
}
```
