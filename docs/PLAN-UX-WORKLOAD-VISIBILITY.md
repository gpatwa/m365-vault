# KavachIQ — UX Workload Visibility & Dashboard Hardening Plan

## Author
Principal Product Manager + UX Engineer | April 2026

## Problem Statement

A prospect who onboarded Patwa Inc with **only Entra ID + Exchange** sees:
1. SharePoint, OneDrive, Teams in the sidebar with full data and "Backup All" buttons
2. Organization page saying "Not Connected" and "0 workloads configured"
3. Jobs page showing 4% success rate (dead-lettered legacy jobs included)
4. License card showing "Workloads: 5" (license limit) instead of "2" (active workloads)

This creates two dangerous impressions:
- **"The product is confusing"** — workloads I didn't choose are backing up my data?
- **"The product is broken"** — Organization says "Not Connected" but Dashboard shows data?

## Competitive Research

| Product | Navigation Pattern | Inactive Workloads |
|---------|-------------------|-------------------|
| **Veeam** | Workload-agnostic sidebar (Organizations, Infrastructure). Workload nodes appear only after data exists in Restore Explorer. | Absent from nav |
| **Druva** | Conditional visibility — sub-navigation per workload appears only after configuration | Absent from nav |
| **Datadog** | Unconfigured integrations in separate "Integrations" marketplace | Separate section |
| **AvePoint** | Shows all workloads but as coverage audit, not navigation | Visible but contextual |
| **HubSpot** | Locked features with red upgrade icons | Widely criticized |

**Industry consensus (2025-2026)**: Hide inactive workloads from primary navigation. Place them in a dedicated "Add Workload" or settings section.

## Root Causes

### Issue 1: Sidebar shows all 5 workloads regardless of what's enabled

**Code**: `frontend/src/components/Layout.tsx` renders the sidebar. It uses the `features` API to determine which workloads the license includes, but doesn't check `workload_lifecycle` status. If the license tier includes SharePoint, it shows SharePoint — even if the user never enabled it.

**Fix**: Sidebar should read from `GET /api/tenants/{id}/workloads` which returns lifecycle status per workload. Only show workloads with lifecycle `enabled`, `discovered`, or `protected`. Show others behind "More Workloads" → "Add Workload" flow.

### Issue 2: Organization page says "Not Connected" / "0 workloads configured"

**Code**: `frontend/src/pages/Organization.tsx` checks `workload_statuses` from `GET /api/tenants/{id}/workloads`. If the prospect onboarded via the legacy single-app flow (before per-workload app separation), no `TenantWorkloadApp` rows exist for Patwa Inc. The page correctly reads "0 configured" from the model, but the reality is the tenant IS connected and backing up.

**Fix**: Organization page should derive connection status from:
- `tenant.status == 'active'` → Connected (not "Not Connected")
- Workload status from `lifecycle_status` field, not `TenantWorkloadApp` existence
- If tenant has protected objects for a workload, show it as "Active" regardless of app provisioning model

### Issue 3: Non-enabled workloads have data (SharePoint, OneDrive, Teams)

**Root cause**: The discovery service discovered ALL workloads for Patwa Inc during onboarding, regardless of which ones the prospect selected. The workload lifecycle model was added after the initial onboarding. Pre-lifecycle tenants have objects for all workloads.

**Fix**: This is a data issue, not a code issue. For existing tenants:
- Workloads the user didn't enable should have lifecycle `disabled`
- Protected objects for disabled workloads should be `UNPROTECTED` (not backing up)
- The scheduler already skips disabled workloads (`_is_workload_protected` check)

### Issue 4: Jobs page shows 4% success rate (dead-lettered jobs)

**Root cause**: The jobs page counts ALL jobs including dead-lettered ones from before the enum fix. Dead-lettered jobs are terminal — they'll never succeed. Including them in the success rate is misleading.

**Fix**: Two options:
- **Option A**: Exclude dead-lettered jobs from success rate calculation (they're not "failed" — they're "abandoned due to a now-fixed bug")
- **Option B**: Add a "Clear Dead Letter" admin action that archives old dead-lettered jobs

### Issue 5: License card shows "Workloads: 5" (license limit)

**Root cause**: The license endpoint counts distinct active workloads from protected objects. Since all 5 workloads were discovered (Issue 3), it shows 5. After fixing Issue 3 (undiscovering non-enabled workloads), this will show 2.

## Proposed Changes

### Phase 1: Sidebar — Show Only Active Workloads (Frontend)

```
WORKLOADS (only enabled workloads)
  Entra ID        ← lifecycle: protected
  Exchange        ← lifecycle: protected

+ Add Workload    ← opens Organization page workload picker

OPERATIONS
  Jobs
  Protection Gaps
  Self Restore
  Recovery
```

Remove "MORE WORKLOADS" section entirely. Replace with "+ Add Workload" link that navigates to Organization settings.

**Files**: `frontend/src/components/Layout.tsx`
**Data source**: `GET /api/tenants/{id}/workloads` → filter by `lifecycle_status in ('enabled', 'discovered', 'protected')`

### Phase 2: Organization Page — Accurate Status (Frontend + Backend)

- Show "Connected" (green) instead of "Not Connected" when `tenant.status == 'active'`
- Show enabled workloads with their actual status from lifecycle model
- Show non-enabled workloads as "Available" with "Enable" toggle
- Remove "Get Started" button for active tenants — replace with workload management

**Files**: `frontend/src/pages/Organization.tsx`, `backend/app/api/tenants.py`

### Phase 3: Clean Up Non-Enabled Workload Data (Backend)

For Patwa Inc:
- Set lifecycle_status = 'disabled' for SharePoint, OneDrive, Teams
- Set protected_objects.status = 'UNPROTECTED' for objects in disabled workloads
- Scheduler already skips disabled workloads — no new backups will be created

**Migration**: One-time SQL for existing pre-lifecycle tenants:
```sql
UPDATE tenant_workload_apps
SET lifecycle_status = 'disabled'
WHERE tenant_id = 4
  AND workload NOT IN ('entra_id', 'exchange');

UPDATE protected_objects
SET status = 'UNPROTECTED', sla_policy_id = NULL
WHERE tenant_id = 4
  AND workload_type NOT IN ('ENTRA_ID', 'EXCHANGE');
```

### Phase 4: Jobs — Exclude Dead-Lettered from Success Rate

- Jobs page hero card "Success Rate" should exclude `dead_letter` status from the denominator
- Success Rate = completed / (completed + failed + partial) — dead_letter is excluded
- Add "Dead Letter" tab showing archived jobs with "Clear All" button for admins

**Files**: `frontend/src/pages/Jobs.tsx`, `backend/app/api/jobs.py`

### Phase 5: License Card — Show Active Workload Count

After Phase 3, the workload count will naturally drop from 5 to 2 because non-enabled workloads won't have protected objects. No additional code change needed.

## Priority Order

1. **Phase 2** (Organization page accuracy) — most confusing page, says "Not Connected" for a connected tenant
2. **Phase 1** (Sidebar cleanup) — removes confusion about available vs active workloads
3. **Phase 3** (Data cleanup) — stops backing up workloads the user didn't choose
4. **Phase 4** (Jobs success rate) — corrects misleading metric
5. **Phase 5** (License card) — auto-fixes after Phase 3

## Effort Estimate

| Phase | Effort | Risk |
|-------|--------|------|
| Phase 1: Sidebar | 2-3 hours | Low — frontend only |
| Phase 2: Organization | 3-4 hours | Medium — frontend + backend logic |
| Phase 3: Data cleanup | 1 hour | Medium — requires careful SQL for existing tenants |
| Phase 4: Jobs metrics | 1-2 hours | Low — calculation change |
| Phase 5: License card | 0 hours | Auto-fixes |

**Total: ~1-1.5 days**

## Success Criteria

After all phases, the prospect user on Patwa Inc should see:
- Sidebar: only Entra ID + Exchange (no SharePoint/OneDrive/Teams)
- Organization: "Connected" status, 2/6 workloads enabled, "+ Add Workload" for others
- Dashboard: 7 objects (Entra ID 1 + Exchange 6), not 25
- Jobs: Success rate reflecting only post-fix jobs
- License: "Workloads: 2" not "5"
- Validation script: `./scripts/validate-user.sh prospect` still passes 24/24
