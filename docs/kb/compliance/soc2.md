# SOC 2 Compliance with Shieldio

SOC 2 audits evaluate an organization's controls against the AICPA Trust Services Criteria. This article maps relevant criteria to Shieldio's controls and explains how to use Shieldio's features as evidence during a SOC 2 examination.

## Trust Services Criteria Mapping

### CC6.1 -- Logical Access Security Software

**Shieldio Controls**: RBAC with Admin, Operator, and Viewer roles. JWT-based authentication with configurable token lifetimes. SSO integration via SAML 2.0 and OpenID Connect.

### CC6.2 -- User Registration and Authorization

**Shieldio Controls**: Admin-controlled user provisioning. Role assignment at creation. Account deactivation (E2003) prevents access without deleting audit history.

### CC6.3 -- Role-Based Access

**Shieldio Controls**: Three-tier RBAC model. Operators can run backups and restores. Viewers have read-only access. Only Admins can modify configuration and manage users.

### CC6.4 -- Access Removal

**Shieldio Controls**: Immediate account disablement. JWT tokens are validated on every request, so disabling an account instantly revokes access regardless of existing tokens.

### CC6.5 -- Authentication Mechanisms

**Shieldio Controls**: Bcrypt-hashed passwords (cost factor 12). SSO with enterprise identity providers supporting MFA. API token authentication for automated workflows.

### CC6.6 -- Boundary Protection

**Shieldio Controls**: TLS 1.2+ enforced on all endpoints. CORS restrictions. Rate limiting (E7001) to prevent abuse. Network-level controls via Azure NSGs in production.

### CC6.7 -- Data Classification and Protection

**Shieldio Controls**: AES-256-GCM encryption at rest with per-tenant DEKs. Per-snapshot key rotation. Separate storage of key material and encrypted data.

### CC6.8 -- Malware Prevention

**Shieldio Controls**: Integrity verification via SHA-256 hashing on backup and restore. Malware detection scanning on restore (E4002). Anomaly detection for unusual backup patterns.

### CC7.1 -- Monitoring Activities

**Shieldio Controls**: Append-only audit log for all user and system actions. Correlation IDs trace requests end-to-end. Health check endpoints for continuous monitoring.

### CC7.2 -- Anomaly Detection

**Shieldio Controls**: Smart Engine baselines for backup size, object count, and change rate. Alerts when metrics deviate significantly from baseline. Circuit breaker patterns detect cascading failures.

### CC7.3 -- Security Incident Response

**Shieldio Controls**: Anomaly alerts notify administrators immediately. Audit logs provide forensic trail. Correlation IDs enable rapid incident investigation.

### CC8.1 -- Change Management

**Shieldio Controls**: All configuration changes are logged in the audit trail. Infrastructure managed via Terraform with version-controlled state. Docker images are immutable and tagged.

### A1.2 -- Recovery

**Shieldio Controls**: Point-in-time recovery from any backup snapshot. Recovery Confidence Score quantifies restore completeness. Granular restore (individual items) and bulk restore (full workload) supported.

## Using Shieldio for SOC 2 Evidence

### Audit Log Exports

The audit log captures every action with timestamp, actor, action type, target resource, result, and correlation ID. Export logs via the API for your auditor:

```
GET /api/audit/export?start=2026-01-01&end=2026-03-31&format=csv
```

### Recovery Confidence Score

The Recovery Confidence Score provides quantitative evidence that backup data can be successfully restored. Include RCS reports as evidence for the A1.2 (Recovery) criterion:

```
GET /api/compliance/rcs/report?tenant_id={id}&period=quarterly
```

### Access Reviews

Export the current user list with roles for periodic access reviews:

```
GET /api/auth/users?include_roles=true&format=csv
```

### Controls Summary

Shieldio maps to **16 SOC 2 controls** across the Common Criteria (CC6, CC7, CC8) and Availability (A1) categories. The following table summarizes coverage:

| Category | Criteria Count | Shieldio Coverage |
|---|---|---|
| CC6 -- Logical and Physical Access | 8 | 8/8 |
| CC7 -- System Operations | 3 | 3/3 |
| CC8 -- Change Management | 1 | 1/1 |
| A1 -- Availability | 1 | 1/1 |
| **Total** | **13 criteria** | **16 controls mapped** |

Some criteria map to multiple Shieldio controls, resulting in 16 total controls across 13 criteria.

## Disclaimer

This document provides a mapping between SOC 2 Trust Services Criteria and Shieldio features. It does not replace a formal SOC 2 audit. Engage a qualified CPA firm to conduct your SOC 2 examination.
