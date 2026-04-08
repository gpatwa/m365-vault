# KavachIQ Production Readiness — Status as of 2026-04-08

## Architecture Overview

```
Browser (React SPA)
  │ httpOnly cookie (session_id)
  ▼
FastAPI Backend (BFF)
  │ Redis session → user context
  │ Cookie auth + JWT fallback
  ▼
┌─────────┬──────────┬───────────┐
│ Redis   │ Postgres │ Azure Blob│
│ Sessions│ Data     │ Backups   │
│ State   │ Models   │ Encrypted │
│ Rate    │ Audit    │ WORM      │
└─────────┴──────────┴───────────┘
```

## Security Posture

| Control | Status | Details |
|---|---|---|
| Auth method | ✅ httpOnly cookie + Redis session | XSS immune, instant revocation |
| CSRF | ✅ SameSite=Lax | Browser won't send cookie cross-origin |
| OAuth callback | ✅ Backend URL | Tokens never in browser |
| Encryption at rest | ✅ AES-256-GCM | Per-tenant DEK, envelope encryption |
| Encryption in transit | ✅ TLS 1.2+ | HTTPS enforced |
| Multi-tenant isolation | ✅ Server-side 403 | resolve_tenant_filter on all endpoints |
| WORM immutability | ✅ Enforced at storage layer | Cannot delete locked snapshots |
| Audit trail | ✅ All actions logged | CSV/JSON export for compliance |
| Rate limiting | ✅ Redis-backed | Cross-pod, per-IP |
| CVEs | ⚠️ 2 remaining | Starlette (requires FastAPI upgrade) |
| Session management | ✅ Redis (24hr TTL) | Survives pod restart |
| Password policy | ✅ 8 chars + uppercase + digit | Self-service change |

## Feature Completeness

| Component | Status | Notes |
|---|---|---|
| Exchange backup | ✅ | Emails, calendar, contacts, rules, archive, public folders, journal |
| Entra ID backup | ✅ | 12 object types, 7 restorable, snapshot diff |
| SharePoint backup | ✅ | Sites, libraries, lists |
| OneDrive backup | ✅ | Files, folders, delta sync |
| Teams backup | ✅ | Channels, chats, files, timestamps preserved |
| Smart Engine | ✅ | Anomaly detection, criticality scoring, health baselines |
| Recovery | ✅ | Confidence scoring, test restore, mass recovery, MVB plans |
| Self-service restore | ✅ | End users restore own items |
| MSP multi-tenant | ✅ | White-label, bulk onboard, billing rollup |
| Billing (Stripe) | ✅ | Checkout, portal, webhooks, 4 tiers |
| Email notifications | ✅ | Backup alerts, nurture, invites |
| Search (⌘K) | ✅ | Intent-aware, cross-workload |
| Audit trail + export | ✅ | CSV/JSON download |
| Security posture | ✅ | 30+ checks, A-F grading |
| User invites | ✅ | Admin invites team members |
| Password management | ✅ | Self-service change, reset via email |
| Prometheus metrics | ✅ | /metrics endpoint for monitoring |
| Per-tenant alerts | ⚠️ Pending | Global alerts only, not per-customer |
| eDiscovery | ⚠️ Roadmap | Enterprise tier, not yet built |
| Full data export | ⚠️ Roadmap | GDPR portability — deferred |

## Test Coverage

| Suite | Count | Status |
|---|---|---|
| BFF auth (cookie/session/logout) | 10 | ✅ |
| Restore consent (Redis-backed) | 10 | ✅ |
| Tenant isolation (403 enforcement) | 12 | ✅ |
| Worker registry (pluggable) | 8 | ✅ |
| Exchange gaps (PST, public folders) | 9 | ✅ |
| Entra restore (7 types, cross-tenant) | 11 | ✅ |
| Self-healing (AIMD, fair scheduler) | 15 | ✅ |
| Workload apps (per-workload Entra) | 25 | ✅ |
| Production readiness (WORM, metrics) | 17 | ✅ |
| **Total** | **117** | **All passing** |

## Infrastructure (Azure)

| Resource | Dev | Prod |
|---|---|---|
| Backend | 0.5 vCPU, 1Gi, 1→3 replicas | 1 vCPU, 2Gi, 2→10 replicas |
| Worker | 0.5 vCPU, 1Gi, 0→3 (KEDA) | 1 vCPU, 2Gi, 2→6 (KEDA) |
| Frontend | 0.25 vCPU, scale-to-zero | 0.25 vCPU, scale-to-zero |
| PostgreSQL | B1ms (1 vCore) | GP_D2s_v3 (2 vCores) |
| Redis | Basic C0 | Standard C1 |
| Storage | LRS | GRS |
| Monthly cost | ~$99 running, ~$22 sleeping | ~$452 |

## Release Process

```
make release ENV=dev
├── test-local (117 unit + 31 integration tests)
├── safe-deploy (build → push → deploy → health gate → auto-rollback)
└── e2e-test (56 Azure endpoint tests)
```

GitHub Actions CI/CD triggers on push to main.

## Remaining Roadmap

| Priority | Item | Effort |
|---|---|---|
| P1 | Per-tenant alert configuration | 2 days |
| P2 | FastAPI/Starlette CVE upgrade | 1 hr |
| P2 | SLA assignment UX (no auto-default) | 1 day |
| P3 | Stripe E2E with real payments | 1 day |
| P3 | eDiscovery (Enterprise tier) | 2 weeks |
| P3 | Full tenant data export (GDPR) | 2 days |
