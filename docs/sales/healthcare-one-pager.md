# KavachIQ for Healthcare — HIPAA-Compliant M365 Backup

---

## The Problem

HIPAA mandates that covered entities maintain recoverable backups of electronic Protected Health Information (ePHI). Microsoft 365's recycle bin retains deleted items for up to 93 days with no encryption controls, no immutability, and no audit trail — none of which satisfy the technical safeguards under 45 CFR 164.312. If a ransomware attack encrypts your Exchange mailboxes or a departing employee deletes patient records from SharePoint, Microsoft's native tools leave you exposed — both operationally and in your next HIPAA audit.

---

## The Solution

KavachIQ provides fully encrypted, auditable, immutable backup for all five Microsoft 365 workloads — purpose-built for healthcare organizations that need to prove HIPAA compliance. Starting at **$1.50/user/month**, KavachIQ closes the backup gap that auditors flag most often.

---

## Key Features

| Feature | What It Does |
|---|---|
| **AES-256-GCM Encryption** | Per-tenant data encryption keys (DEKs) wrapped by a master key. Encryption at rest and in transit. |
| **WORM Immutable Storage** | Write-once, read-many storage prevents ransomware or insider tampering with backup data. |
| **Audit Trail** | Every backup, restore, and administrative action is logged with timestamps and user identity. |
| **5 Workloads** | Exchange, OneDrive, SharePoint, Teams, and Entra ID (formerly Azure AD) — including directory config. |
| **Anomaly Detection** | AI-powered monitoring flags unusual deletion patterns or mass changes before they become incidents. |
| **Recovery Plans** | Pre-built and testable recovery runbooks with confidence scoring to prove recoverability to auditors. |

---

## HIPAA Technical Safeguard Mapping

| HIPAA Requirement | 45 CFR Section | How KavachIQ Addresses It |
|---|---|---|
| **Access Control** | 164.312(a)(1) | Role-based access, per-tenant isolation, MFA-protected admin console |
| **Audit Controls** | 164.312(b) | Immutable audit logs for every backup, restore, and config change |
| **Integrity Controls** | 164.312(c)(1) | SHA-256 content verification, WORM storage prevents alteration |
| **Person or Entity Authentication** | 164.312(d) | Entra ID integration with MFA; service principal authentication |
| **Transmission Security** | 164.312(e)(1) | TLS 1.3 in transit, AES-256-GCM at rest |
| **Contingency Plan (Backup)** | 164.308(a)(7) | Automated daily backups with point-in-time restore and recovery testing |

---

## Pricing

| Plan | Price | Includes |
|---|---|---|
| **Free** | $0 (up to 25 users) | All 5 workloads, 30-day retention, basic support |
| **Professional** | $1.50/user/month | Extended retention, anomaly detection, priority support |
| **Business** | $3.00/user/month | WORM immutable storage, legal hold, 1-year retention, audit reports |
| **Enterprise** | $5.00/user/month | Self-hosted option, custom retention, dedicated support, SLA guarantee |

---

## Get Started

Start free at **kavachiq.com** — protect your first 25 users in under 10 minutes with zero infrastructure to manage.

Need a walkthrough? Contact sales at **sales@kavachiq.com** or schedule a demo at **kavachiq.com/demo**.
