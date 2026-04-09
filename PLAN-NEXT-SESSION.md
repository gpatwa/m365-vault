# KavachIQ — Enterprise Release Readiness Plan

## Session Context

**Date**: April 9, 2026
**Branch**: `main` (all work merged)
**Deployed**: kavachiq.com
**Tests**: 768 backend + 50 frontend + 70 E2E (all passing)

## What Was Shipped This Session

| Feature | Status |
|---------|--------|
| Batch scheduler (parent-child jobs, 500-item batches) | Deployed |
| Anomaly detection ceiling (dedup, auto-resolve, TTL) | Deployed |
| Server-side onboarding state machine | Deployed |
| KEDA auto-scaling fix (was watching wrong queue) | Deployed |
| Atomic seed data module | Deployed |
| Tenant isolation fix (6 cross-tenant data leaks) | Deployed |
| Prometheus observability (prometheus-client, histograms) | Deployed |
| Encryption key versioning (zero-downtime rotation) | Deployed |
| Secret expiry monitoring + diagnostics | Deployed |
| Cost attribution (Redis metering, cost breakdown API) | Deployed |
| Security scan + 10 findings fixed | Deployed |

## P0 — Ship Blockers (Must Fix Before Any Customer)

### 1. Fix 54 Failing Tests
**Risk**: HIGH — 93% pass rate is not shippable
**Root cause**: Mostly 403 errors — test fixtures create users without tenant memberships, same pattern as the demo user bug we fixed. The tests that fail are all in modules that require tenant access (recovery, restore, teams, org_context, MVB plan, entra_id).
**Fix**: Update test fixtures to create proper UserTenantMembership records.
**Effort**: 2-3 hours

### 2. Root-Cause 1.3% Backup Success Rate
**Risk**: CRITICAL — product doesn't work if backups fail
**Symptoms**: Pre-existing issue from previous session. Backend "degraded" status.
**Investigation needed**:
- Check Graph API token refresh (are tokens expiring mid-backup?)
- Check connection pool exhaustion (pool_size=25, max_overflow=50)
- Check worker logs for common error patterns
- Check if demo tenant's M365 connector secret has expired
**Effort**: 2-4 hours (investigation) + fix time

### 3. Upgrade Vulnerable Dependencies
**Risk**: HIGH — CVEs in auth (JWT) and encryption (AES-256)
**Packages**:
- `python-jose==3.3.0` → `3.4.0` (PYSEC-2024-232, PYSEC-2024-233)
- `cryptography==43.0.1` → `46.0.6` (CVE-2024-12797, CVE-2026-26007, CVE-2026-34073)
**Verification**: Run encryption round-trip tests + JWT login flow after upgrade
**Effort**: 1 hour

### 4. Activate Alembic Migrations
**Risk**: HIGH — no way to safely change schema in production
**Steps**:
1. `alembic revision --autogenerate -m "baseline"` (generates initial migration)
2. `alembic stamp head` on production DB (marks as already applied)
3. Add `alembic upgrade head` to Dockerfile CMD
4. Remove ad-hoc ALTER TABLE from main.py and database.py (next release)
**Effort**: 2 hours

### 5. Grafana + Alerting
**Risk**: HIGH — metrics exist but nobody watches
**Alert rules needed**:
- Backup failure rate > 10% (5-minute window) → PagerDuty critical
- Queue depth > 100 for > 10 minutes → PagerDuty warning
- Health score < 50 for any tenant → PagerDuty warning
- Secret expiring < 7 days → PagerDuty warning
- Worker pod count = 0 for > 5 minutes → PagerDuty critical
- HTTP error rate > 5% → PagerDuty warning
**Effort**: 1 day

## P1 — Before Enterprise Sales Motion

### 6. Load Testing
- 50 tenants × 1,000 mailboxes
- Verify batch scheduler splits correctly
- Measure: backup throughput (MB/s), queue drain time, Graph API throttle rate
- **Effort**: 1 day

### 7. Incident Runbook
- Worker pods stuck → restart, check Redis
- Redis OOM → flush metering keys, check for queue backlog
- Database connection pool → check pool_utilization metric, increase pool_size
- Graph API mass throttling → check AIMD limiter, reduce WORKER_CONCURRENCY
- Backup failure spike → check Graph token, connector secret expiry
- **Effort**: 1 day

### 8. SOC 2 Documentation
- Data flow diagrams (client → CDN → API → worker → Graph API → Azure Blob)
- Encryption documentation (KEK/DEK, AES-256-GCM, envelope encryption)
- Access control matrix (roles, tenant isolation, RLS roadmap)
- Data retention policy (SLA-based, WORM support, legal hold)
- Incident response plan (based on runbook + alerting)
- **Effort**: 3-5 days

### 9. Backup Validation Pipeline
- Connect validation to batch scheduler
- After parent job aggregates: auto-validate random 10% sample
- Track validation_status on Snapshot model (already has the field)
- **Effort**: 1 day

### 10. Multi-Region / DR
- Active-passive: primary (eastus) + standby (westus2)
- Azure Blob GRS already configured for prod (geo-redundant)
- Database: Azure Flexible Server read replica in secondary region
- DNS failover via Cloudflare (already on Cloudflare)
- **Effort**: 1 week

## P2 — Expected Within 6 Months

| Item | Notes |
|------|-------|
| Audit log export (CSV/SIEM) | Audit log exists, needs export endpoint |
| SSO enforcement per-tenant | SSO implemented but optional |
| Data residency controls | Per-tenant storage region selection |
| Per-tenant API rate limits | Current limiting is per-user, not per-tenant |
| Webhook notifications | Callback on backup completion/failure |
| PostgreSQL Row-Level Security | Defense-in-depth (app-level filtering done) |

## How to Start Next Session

```bash
# Verify everything works
make dev                         # Start Docker Compose
make test-backend                # 768+ pass
make test-pg                     # 221+ pass
cd frontend && npx vitest run    # 50 pass

# Deploy
make safe-deploy ENV=dev         # 70/70 E2E pass
```

**First tasks**: Items 1-4 (fix failing tests, backup success rate, dependency upgrades, Alembic activation).
