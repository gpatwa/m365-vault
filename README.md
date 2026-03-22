# M365 Vault

**Enterprise Backup & Recovery for Microsoft 365**

M365 Vault is a self-hosted SaaS data protection platform for Microsoft 365 workloads. It provides automated, SLA-driven backup and granular point-in-time restore for Exchange Online, OneDrive for Business, and SharePoint Online — with AES-256 encryption at rest, role-based access control, and comprehensive audit logging.

> Version 1.5.0 | Python 3.11+ | React 19 | FastAPI | Apache-2.0 License

---

## Key Features

- **Multi-tenant M365 protection** across Exchange, OneDrive, and SharePoint workloads
- **SLA policy-driven scheduling** with configurable backup frequency and retention periods
- **Point-in-time restore** with four modes: full in-place, item-level, cross-user, and export
- **Microsoft Graph API integration** with OAuth2 client credentials, rate limiting (429 handling), exponential backoff with jitter, and batch operations
- **AES-256-GCM envelope encryption** using a two-layer DEK/KEK key scheme for data at rest
- **Storage efficiency** with zstd compression (70-85% reduction on JSON), SHA-256 content-addressable deduplication, and CDC chunking for large files
- **Failed item tracking** with 13 error categories and actionable resolution guidance
- **Automatic retry engine** with exponential backoff for failed backup jobs
- **Role-based access control** with three roles: Admin, Operator, Viewer
- **Comprehensive audit logging** with severity levels and full-text search
- **Workload swimlane dashboard** with per-workload stats, progress bars, and click-to-expand drill-down
- **Retention management** with automated expired snapshot cleanup
- **Mass recovery** operations for bulk restore across workloads
- **50+ REST API endpoints** with auto-generated OpenAPI documentation

---

## Architecture

```
                          +-------------------+
                          |   React Frontend  |
                          |  (nginx / Vite)   |
                          +--------+----------+
                                   |
                                   | REST API (JWT Auth)
                                   |
                          +--------v----------+
                          |  FastAPI Backend   |
                          |  (Port 8000)      |
                          +---+------+----+---+
                              |      |    |
              +---------------+      |    +----------------+
              |                      |                     |
     +--------v--------+   +--------v--------+   +--------v--------+
     |   PostgreSQL 16  |   | Microsoft Graph |   | Encrypted Object|
     |  (SQLAlchemy)    |   | API (MSAL)      |   | Storage (AES)   |
     +---------+--------+   +-----------------+   | MinIO / Azure   |
               |                                  +-----------------+
     +---------v------------------+
     | Background Jobs            |
     | - Backup Scheduler (60s)   |
     | - Retention Cleanup (6h)   |
     | - Retry Engine (10m)       |
     +----------------------------+
```

---

## Tech Stack

| Layer     | Technology |
|-----------|-----------|
| Backend   | Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, aiosqlite, MSAL, APScheduler, cryptography, zstandard |
| Frontend  | React 19, TypeScript 5.9, TailwindCSS 3.4, Recharts 3.8, TanStack Query 5, React Router 7, Vite 8 |
| Database  | PostgreSQL 16 (Docker local / Azure Flexible Server production) |
| Auth      | JWT (python-jose), bcrypt password hashing |
| Encryption| AES-256-GCM envelope encryption |

---

## Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+
- Azure AD App Registration with application permissions:
  - `Mail.Read`, `Calendars.Read`, `Contacts.Read` (Exchange)
  - `Files.Read.All` (OneDrive)
  - `Sites.Read.All` (SharePoint)
  - `User.Read.All` (Discovery)

### 1. Clone & Setup Backend

```bash
git clone <repo-url> && cd m365-data-protection

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your SECRET_KEY and ENCRYPTION_MASTER_KEY
```

### 3. Start Backend

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Setup & Start Frontend

```bash
cd frontend
npm install
npm run dev
```

### 5. Access the Application

Open [http://localhost:5173](http://localhost:5173) and register your first admin account.

### Docker Compose (Recommended)

Run the full stack with PostgreSQL + MinIO + Backend + Frontend:

```bash
docker compose up -d

# Seed test data
docker compose exec backend python3 /scripts/simulate_backup_data.py

# Open UI at http://localhost:5173 (login: admin / admin123)
# MinIO Console at http://localhost:9001 (login: minioadmin / minioadmin)
```

### Make Commands

All common operations are available via `make`:

```bash
make help             # Show all available commands

# Local Development
make dev              # Start full Docker Compose stack (build + run)
make dev-bg           # Start in background
make dev-down         # Stop all services
make dev-clean        # Stop + remove volumes (fresh start)
make seed             # Seed simulated backup data
make seed-clean       # Clean DB + storage, then re-seed
make build            # Build Docker images locally

# Azure Deployment
make bootstrap        # One-time Azure + GitHub setup (SP, OIDC, tfstate, secrets)
make tf-plan          # Plan infrastructure changes (ENV=dev|prod)
make tf-apply         # Apply infrastructure changes
make acr-push         # Build + push Docker images to ACR
make tf-set-acr-secrets  # Set ACR GitHub secrets from Terraform output
make deploy-dev       # Trigger dev deployment via GitHub Actions
make deploy-prod      # Trigger prod deployment (with confirmation)
make deploy-status    # Show recent CI/CD runs

# Cost Management
make az-sleep         # Pause all Azure resources (scale to 0 + stop DB)
make az-wake          # Resume all Azure resources
make az-status        # Show current Azure resource status
make az-cleanup       # Full Azure teardown + state reset
```

---

## Project Structure

```
m365-data-protection/
├── backend/
│   ├── app/
│   │   ├── api/           # 10 API routers (auth, tenants, exchange, etc.)
│   │   ├── models/        # 9 SQLAlchemy models (incl. dedup index)
│   │   ├── services/      # 12 business services (incl. compression, dedup)
│   │   ├── workers/       # 3 workload backup workers
│   │   ├── utils/         # Retry utilities & error classification
│   │   ├── config.py      # Application settings
│   │   ├── database.py    # Async database setup
│   │   └── main.py        # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # 10 page components
│   │   ├── components/    # Shared UI components (incl. jobs/ swimlanes)
│   │   ├── api/           # API client
│   │   ├── hooks/         # Custom React hooks
│   │   ├── utils/         # Shared utilities (format, etc.)
│   │   └── types/         # TypeScript type definitions
│   └── package.json
├── scripts/               # Simulation, discovery & provisioning scripts
├── infra/                 # Terraform IaC (Azure Container Apps)
├── .github/workflows/     # CI/CD (GitHub Actions)
├── docs/                  # Documentation
├── .env.example           # Configuration template
└── CHANGELOG.md           # Release history
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Azure Deployment](docs/AZURE_DEPLOYMENT.md) | Deploy to Azure with Terraform + GitHub Actions |
| [Onboarding Guide](docs/ONBOARDING.md) | Step-by-step tenant setup and first backup |
| [Tenant Security](docs/TENANT_SECURITY.md) | Credential encryption, data isolation, least-privilege access, RBAC |
| [API Reference](docs/API_REFERENCE.md) | Complete REST API documentation (50+ endpoints) |
| [Architecture](docs/ARCHITECTURE.md) | System design, data model, and service architecture |
| [Compliance Report](docs/COMPLIANCE_REPORT.md) | Security controls, encryption, and regulatory alignment |
| [Product Roadmap](docs/M365_Vault_Product_Roadmap.docx) | Strategic roadmap, competitive analysis, and pricing strategy |

---

## API Documentation

Interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) when the backend is running.

---

## License

Apache-2.0 License. See [LICENSE](LICENSE) for details.
