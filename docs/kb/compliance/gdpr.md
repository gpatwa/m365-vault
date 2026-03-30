# GDPR Compliance with Shieldio

The General Data Protection Regulation (GDPR) imposes strict requirements on organizations that process personal data of EU residents. This article maps key GDPR articles to Shieldio's technical controls and explains how the platform supports your data protection obligations.

## Article Mapping

### Article 5(1)(f) -- Integrity and Confidentiality

**Requirement**: Personal data must be processed with appropriate security, including protection against unauthorized access, accidental loss, or destruction.

**Shieldio Controls**:
- AES-256-GCM encryption for all backup data at rest.
- Per-tenant Data Encryption Keys (DEKs) ensure tenant isolation at the cryptographic level.
- SHA-256 content hashing verifies data integrity on every restore operation.
- TLS 1.2+ for all data in transit.

### Article 17 -- Right to Erasure

**Requirement**: Data subjects have the right to request deletion of their personal data.

**Shieldio Controls**:
- Tenant purge functionality permanently removes all backup data, encryption keys, and metadata for a specific tenant.
- Per-snapshot DEK architecture means destroying the encryption key renders snapshot data unrecoverable, enabling cryptographic erasure.
- Purge operations are recorded in the audit log for compliance evidence.

### Article 25 -- Data Protection by Design and by Default

**Requirement**: Implement appropriate technical measures to ensure data protection principles are embedded in processing.

**Shieldio Controls**:
- Per-snapshot DEKs limit the blast radius of any key compromise to a single backup snapshot.
- Minimum-privilege RBAC roles (Viewer, Operator, Admin) enforce least-access by default.
- New users are assigned the most restrictive role until explicitly promoted.

### Article 30 -- Records of Processing Activities

**Requirement**: Maintain a record of processing activities under your responsibility.

**Shieldio Controls**:
- Append-only audit log records every backup, restore, access, and configuration event.
- Each entry includes: actor, action, target resource, timestamp, result, and correlation ID.
- Audit logs are exportable in CSV and JSON formats for inclusion in your Article 30 register.

### Article 32 -- Security of Processing

**Requirement**: Implement appropriate technical and organizational measures to ensure a level of security appropriate to the risk.

**Shieldio Controls**:
- Encryption: AES-256-GCM at rest, TLS 1.2+ in transit.
- Access control: RBAC with JWT authentication and optional SSO/MFA.
- Backup and recovery: Automated backups with verified restore capability (Recovery Confidence Score).
- Resilience: Exponential backoff, circuit breakers, and self-healing retry ensure backup continuity.

### Article 33 -- Notification of a Personal Data Breach

**Requirement**: Notify the supervisory authority within 72 hours of becoming aware of a personal data breach.

**Shieldio Controls**:
- Anomaly detection identifies unusual patterns such as mass deletion, unexpected data volume changes, or unauthorized access attempts.
- Alerts notify administrators immediately when anomalies are detected.
- Audit logs provide the forensic detail needed to assess breach scope and impact within the 72-hour window.

## Data Residency

Shieldio deployments on Azure allow you to select the region where backup data is stored. This supports compliance with GDPR data residency preferences and any additional requirements from local supervisory authorities.

When configuring your deployment:
- Choose an Azure region within the EU (e.g., West Europe, North Europe) if your data subjects are EU residents.
- Backup data, encryption keys, and metadata all reside in the selected region.
- Cross-region replication, if enabled, can be restricted to EU regions only.

## Right to Erasure Process

To fulfill an Article 17 erasure request for data within Shieldio backups:

1. Identify the tenant and objects associated with the data subject.
2. Execute a tenant purge or selective object deletion via the API.
3. Shieldio destroys the associated DEKs, rendering encrypted data unrecoverable.
4. Export the audit log entry as evidence of deletion for your records.

Note: Selective object-level deletion is available on Business and Enterprise tiers. Community and Professional tiers support full tenant purge.

## Disclaimer

This document maps GDPR articles to Shieldio's technical capabilities. It does not constitute legal advice. Consult a qualified Data Protection Officer or legal counsel to determine your specific GDPR obligations.
