# Shieldio

**SaaS Data Protection Platform — Protect Your Cloud Data**

Shieldio is an open-source, self-hosted SaaS data protection platform. Currently protects Microsoft 365 workloads with a roadmap to support Google Workspace, Salesforce, and more. Features AI-powered intelligence, immutable storage, and enterprise-grade security — all at zero marginal cost.

> Version 2.3.0 | 152 API routes | 320 tests | Python 3.12+ | React 19 | FastAPI | Apache-2.0

---

## Key Features

### 5 Workloads Protected
- **Exchange Online** — Emails, calendar events, contacts, attachments
- **OneDrive for Business** — Files, folders with version tracking
- **SharePoint Online** — Sites, document libraries, lists, list items
- **Microsoft Teams** — Channel messages (Export API), files, 1-to-1/group chats, team settings
- **Entra ID (Azure AD)** — 12 object types: users, groups, roles, CA policies, apps, service principals, admin units, OAuth grants, devices, domains. Snapshot diff/compare for configuration drift detection

### Intelligent Platform
- **Smart Engine** — Statistical anomaly detection, health scoring (0-100), baseline tracking
- **Org Context** — Auto-detected organizational hierarchy, VIP groups, criticality scoring from Graph API
- **MVB Recovery Plans** — Pre-computed 4-phase NIST-ordered recovery plans with criticality-weighted confidence
- **Self-Healing** — Auto-retry with exponential backoff, error categorization (13 types), intelligent remediation
- **Sensitive Data Scanner** — PII/PHI/PCI regex detection in backup data ($0 vs Purview $5-10/user)
- **Backup Validation** — Automated checksum verification with sampling
- **Recovery Dashboard** — Confidence score (0-100), RPO/RTO compliance, 5 recovery runbooks, mass recovery

### Production Resilience
- **Error code system** — 30+ structured error codes (E1xxx-E7xxx) with actionable fix suggestions
- **Circuit breaker** — Per-tenant Graph API circuit breaker with auto-recovery
- **Pre-flight validation** — Checks Graph API, storage, and database before starting operations
- **Idempotency** — X-Idempotency-Key header support for safe mutation retries
- **Correlation tracing** — X-Correlation-ID flows through frontend, backend, and Graph API calls
- **Toast notifications + ErrorBoundary** — User-facing error handling with copy-able correlation IDs

### Enterprise Security
- **AES-256-GCM encryption** with per-snapshot DEK/KEK key hierarchy
- **WORM immutable storage** with retention locks and legal hold
- **SSO/MFA** via Entra ID OIDC (MSAL) with auto-provisioning
- **Tiered rate limiting** — auth (20/min), onboarding (60/min), API (600/min)
- **Structured JSON logging** with correlation IDs and request tracing
- **Audit logging** with severity levels and full-text search

### Operations
- **SLA policy engine** with configurable frequency, retention, and WORM
- **Tenant lifecycle** — onboard, deactivate, reactivate, purge
- **Permission auto-provisioning** — Graph API permissions added and consented automatically
- **Reports & Analytics** — backup performance, storage, failures, SLA compliance, security
- **Usage & License tracking** — per-tenant usage, tier enforcement, growth trends

### Architecture
- **Control Plane / Data Plane separation** with BaseWorker framework
- **Job dispatcher** (in-process or Redis queue) for scalable worker execution
- **Circuit breaker** for Graph API resilience
- **Stale job detection** with automatic re-queue

---

## Architecture

```
Control Plane (API)                    Data Plane (Workers)
┌─────────────────────────┐           ┌─────────────────────────┐
│ FastAPI (152 routes)     │           │ BaseWorker Framework    │
│ Scheduler (SLA checks)   │           │ ├── ExchangeWorker     │
│ Smart Engine (analytics) │  Redis    │ ├── OneDriveWorker     │
│ Alert Service            │ ──Queue→  │ ├── SharePointWorker   │
│ Auth / SSO (OIDC)        │           │ ├── TeamsWorker        │
│ Reports / Usage          │           │ └── EntraIDWorker      │
│ Audit Logging            │           │ Storage Pipeline       │
└──────────┬──────────────┘           │ Encryption Service     │
           │                           └──────────┬──────────────┘
     ┌─────┴─────┐                          ┌─────┴─────┐
     │ PostgreSQL │                          │ Blob Store │
     │ (metadata) │                          │ (Azure/S3) │
     └───────────┘                          └───────────┘
```

---

## Tech Stack

| Layer     | Technology |
|-----------|-----------|
| Backend   | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), MSAL, APScheduler, cryptography, zstandard |
| Frontend  | React 19, TypeScript 5.9, TailwindCSS, Recharts, TanStack Query, React Router, Vite |
| Database  | PostgreSQL 16 (Docker local / Azure Flexible Server production) |
| Auth      | JWT + refresh tokens, bcrypt, Entra ID OIDC (MSAL) |
| Encryption| AES-256-GCM envelope encryption (DEK/KEK) |
| Storage   | Pluggable: Local filesystem, MinIO (S3), Azure Blob Storage |
| Testing   | pytest (320 unit + integration + chaos), k6 (load), Playwright (E2E) |
| Infra     | Docker Compose (dev), Azure Container Apps + Terraform (prod), GitHub Actions CI/CD |

---

## Quickstart

### Docker Compose (Recommended)

```bash
git clone <repo-url> && cd shieldio
docker compose up -d

# Open UI at http://localhost:5173 (login: admin / admin123)
```

### Make Commands

```bash
make help             # Show all available commands
make dev              # Start full Docker Compose stack
make dev-down         # Stop all services

# Azure
make bootstrap        # One-time Azure + GitHub setup
make acr-push         # Build + push Docker images to ACR
make tf-apply         # Deploy infrastructure
make az-sleep         # Pause Azure resources ($20/mo sleeping)
make az-wake          # Resume Azure resources
```

---

## Project Structure

```
shieldio/
├── backend/
│   ├── app/
│   │   ├── api/           # 31 API routers (152 routes)
│   │   ├── models/        # 13 SQLAlchemy models (tenant, object, snapshot, job, health, org_context, audit)
│   │   ├── services/      # 31 business services (backup, restore, resilience, circuit breaker, smart engine, encryption)
│   │   ├── workers/       # 5 workload workers + BaseWorker framework
│   │   ├── interfaces/    # Dispatcher (in-process / Redis)
│   │   ├── errors.py      # Structured error codes (E1xxx-E7xxx)
│   │   └── main.py        # FastAPI app with middleware stack
│   └── tests/             # 320 tests (unit, integration, chaos)
├── frontend/
│   ├── src/
│   │   ├── pages/         # 20+ page components
│   │   ├── components/    # Design system, DataTable, CommandPalette
│   │   ├── config/        # Centralized workload + platform config
│   │   └── contexts/      # Auth context
│   └── e2e/               # Playwright E2E tests
├── scripts/               # Discovery, data creation, DB migration
├── infra/                 # Terraform IaC (Azure Container Apps)
├── .github/workflows/     # CI/CD (GitHub Actions)
├── docs/                  # Documentation + landing page
├── k6/                    # Load test scripts
└── CHANGELOG.md           # Release history
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Azure Deployment](docs/AZURE_DEPLOYMENT.md) | Deploy to Azure with Terraform + GitHub Actions |
| [Architecture](docs/ARCHITECTURE.md) | System design, CP/DP separation, BaseWorker framework |
| [API Reference](docs/API_REFERENCE.md) | Complete REST API documentation (152 endpoints) |
| [Cost Analysis](docs/COST_MARGIN_ANALYSIS.md) | Pricing tiers, infrastructure costs, margin analysis |
| [Production Resilience](docs/PRODUCTION_RESILIENCE_DESIGN.md) | Error codes, circuit breaker, pre-flight, idempotency |
| [Onboarding Guide](docs/ONBOARDING.md) | Tenant setup and first backup |
| [Tenant Security](docs/TENANT_SECURITY.md) | Encryption, isolation, RBAC, WORM |
| [Compliance Report](docs/COMPLIANCE_REPORT.md) | Security controls and regulatory alignment |

Interactive API docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Roadmap

- [x] Phase 1: Enterprise Foundation (Exchange, OneDrive, SharePoint, Teams, Entra ID)
- [x] Phase 2: Intelligence (Smart Engine, Sensitive Data, Validation, Self-Restore)
- [x] Production Readiness (tests, security, logging, CI/CD)
- [x] Phase 2.5A: Org Context Layer — Smart Backup (auto-detected criticality, VIP groups, 4-factor scoring)
- [x] Phase 2.5B: Org Context Layer — Smart Recovery (pre-computed MVB plans, criticality-weighted confidence)
- [x] Production Resilience Week 1: Error codes (E1xxx-E7xxx), structured logging, correlation tracing, toast/ErrorBoundary
- [x] Production Resilience Week 2: Circuit breaker, pre-flight checks, idempotency keys, diagnostics endpoints
- [x] Option B Pricing: 4-tier competitive pricing (Free/$1.50/$3.00/$5.00)
- [ ] Production Resilience Week 3-4: Deployment health gate, automated rollback, status page
- [ ] Phase 2.5C: Threat-Informed Recovery (OCSF ingestion, clean point detection, SIEM integration)
- [ ] Phase 2.5D: Agentic Recovery (Claude multi-stage verification, NL plan adjustment)
- [ ] Phase 2.5E: Cleanroom Recovery (isolated restore to scratch tenant, scan, validate, promote)
- [ ] Scale Infrastructure: Cloudflare CDN/DDoS, Redis rate limiting, API gateway (Azure APIM or Kong)
- [ ] Phase 3: Power Platform, MSP Console, eDiscovery, SIEM, Kubernetes
- [ ] Phase 4: Google Workspace, Salesforce, NL Search (BYOK)

---

## License

Apache-2.0 License. See [LICENSE](LICENSE) for details.
