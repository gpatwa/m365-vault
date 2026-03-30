# HIPAA Compliance with Shieldio

Organizations that handle Protected Health Information (PHI) must comply with the HIPAA Security Rule. This article maps HIPAA technical safeguard requirements to Shieldio's built-in controls, helping covered entities and business associates evaluate Shieldio as part of their compliance program.

## Technical Safeguards Mapping

### 164.312(a)(1) -- Access Control

**Requirement**: Implement technical policies and procedures to allow access only to authorized persons.

**Shieldio Controls**:
- Role-Based Access Control (RBAC) with three built-in roles: Admin, Operator, and Viewer.
- JWT-based session tokens with configurable expiration.
- Per-tenant isolation ensures users in one tenant cannot access another tenant's data.
- All access decisions are enforced at the API layer before any data is returned.

### 164.312(a)(2)(iv) -- Encryption and Decryption

**Requirement**: Implement a mechanism to encrypt and decrypt electronic PHI.

**Shieldio Controls**:
- AES-256-GCM encryption for all backup data at rest.
- Per-tenant Data Encryption Keys (DEKs) wrapped by a master Key Encryption Key (KEK).
- Per-snapshot DEK rotation ensures that compromising one snapshot does not expose others.
- Key material is stored separately from encrypted data.

### 164.312(b) -- Audit Controls

**Requirement**: Implement mechanisms to record and examine activity in systems containing ePHI.

**Shieldio Controls**:
- Append-only audit log captures every authentication, authorization, backup, restore, and configuration change.
- Audit entries include actor, action, target resource, timestamp, and correlation ID.
- Audit logs are immutable and retained for the configured retention period.
- Logs are exportable for SIEM integration.

### 164.312(c)(1) -- Integrity

**Requirement**: Implement policies and procedures to protect ePHI from improper alteration or destruction.

**Shieldio Controls**:
- SHA-256 content hashing for every backed-up object.
- Integrity verification on restore ensures data has not been tampered with.
- Recovery Confidence Score validates that restored data matches the original.

### 164.312(d) -- Person or Entity Authentication

**Requirement**: Implement procedures to verify the identity of persons seeking access.

**Shieldio Controls**:
- Password authentication with bcrypt hashing (cost factor 12).
- SSO integration via SAML 2.0 and OpenID Connect for enterprise identity providers.
- Optional multi-factor authentication through the connected identity provider.

### 164.312(e)(1) -- Transmission Security

**Requirement**: Implement security measures to guard against unauthorized access to ePHI during transmission.

**Shieldio Controls**:
- TLS 1.2 or higher enforced on all API endpoints.
- HTTPS-only communication between the dashboard, backend, and storage layer.
- Graph API calls to Microsoft use Microsoft's TLS-secured endpoints.

## Business Associate Agreement (BAA)

If Shieldio processes, stores, or transmits PHI on behalf of a covered entity, a Business Associate Agreement is required. Contact sales@shieldio.com to request a BAA. The BAA covers Shieldio's obligations regarding PHI in backup data, breach notification procedures, and data return or destruction on termination.

## PHI in Backup Data

Microsoft 365 mailboxes, OneDrive files, and SharePoint sites may contain PHI. When Shieldio backs up these workloads:

- All data is encrypted at rest with AES-256-GCM before being written to storage.
- Data in transit is protected by TLS 1.2+.
- Access to backup data requires authentication and appropriate RBAC role.
- Restore operations are logged in the audit trail with full details.

## Retention Requirements

HIPAA requires that documentation be retained for six years. Shieldio's configurable retention policies can be set to meet or exceed this requirement. The Business and Enterprise tiers support retention periods up to 7 years.

## Disclaimer

This document provides a technical mapping between HIPAA requirements and Shieldio features. It does not constitute legal advice. Organizations should consult qualified legal and compliance professionals to determine their specific HIPAA obligations.
