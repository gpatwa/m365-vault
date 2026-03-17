# M365 Vault

**Enterprise Backup & Recovery for Microsoft 365**

M365 Vault is a self-hosted SaaS data protection platform for Microsoft 365 workloads. It provides automated, SLA-driven backup and granular point-in-time restore for Exchange Online, OneDrive for Business, and SharePoint Online — with AES-256 encryption at rest, role-based access control, and comprehensive audit logging.

> Version 1.0.0 | Python 3.11+ | React 19 | FastAPI | MIT License

---

## Key Features

- **Multi-tenant M365 protection** across Exchange, OneDrive, and SharePoint workloads
- **SLA policy-driven scheduling** with configurable backup frequency and retention periods
- **Point-in-time restore** with four modes: full in-place, item-level, cross-user, and export
- **Microsoft Graph API integration** with OAuth2 client credentials, rate limiting (429 handling), exponential backoff with jitter, and batch operations
- **AES-256-GCM envelope encryption** using a two-layer DEK/KEK key scheme for data at rest
- **Failed item tracking** with 13 error categories and actionable resolution guidance
- **Automatic retry engine** with exponential backoff for failed backup jobs
- **Role-based access control** with three roles: Admin, Operator, Viewer
- **Comprehensive audit logging** with severity levels and full-text search
- **Dashboard** with SLA compliance monitoring, backup activity charts, and collapsible unprotected item visibility
- **Retention management** with automated expired snapshot cleanup
- **Mass recovery** operations for bulk restore across workloads
- **50+ REST API endpoints** with auto-generated OpenAPI documentation

---

## Architecture

```
                          +-------------------+
                          |   React Frontend  |
                          |  (Port 5173)      |
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
     | SQLite Database  |   | Microsoft Graph |   | Encrypted File  |
     | (SQLAlchemy)     |   | API (MSAL)      |   | Storage (AES)   |
     +---------+--------+   +-----------------+   +-----------------+
               |
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
| Backend   | Python 3.11+, FastAPI 0.115, SQLAlchemy 2.0, aiosqlite, MSAL, APScheduler, cryptography |
| Frontend  | React 19, TypeScript 5.9, TailwindCSS 3.4, Recharts 3.8, TanStack Query 5, React Router 7, Vite 8 |
| Database  | SQLite (dev) / PostgreSQL (production) |
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

---

## Project Structure

```
m365-data-protection/
├── backend/
│   ├── app/
│   │   ├── api/           # 10 API routers (auth, tenants, exchange, etc.)
│   │   ├── models/        # 8 SQLAlchemy models
│   │   ├── services/      # 10 business services
│   │   ├── workers/       # 3 workload backup workers
│   │   ├── utils/         # Retry utilities & error classification
│   │   ├── config.py      # Application settings
│   │   ├── database.py    # Async database setup
│   │   └── main.py        # FastAPI app entry point
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/         # 10 page components
│   │   ├── components/    # Shared UI components
│   │   ├── api/           # API client
│   │   ├── hooks/         # Custom React hooks
│   │   └── types/         # TypeScript type definitions
│   └── package.json
├── docs/                  # Documentation
├── .env.example           # Configuration template
└── CHANGELOG.md           # Release history
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Onboarding Guide](docs/ONBOARDING.md) | Step-by-step tenant setup and first backup |
| [API Reference](docs/API_REFERENCE.md) | Complete REST API documentation (50+ endpoints) |
| [Architecture](docs/ARCHITECTURE.md) | System design, data model, and service architecture |
| [Compliance Report](docs/COMPLIANCE_REPORT.md) | Security controls, encryption, and regulatory alignment |

---

## API Documentation

Interactive API docs are available at [http://localhost:8000/docs](http://localhost:8000/docs) when the backend is running.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
