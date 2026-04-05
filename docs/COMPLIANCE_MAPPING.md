# KavachIQ Compliance Mapping

Maps KavachIQ security controls to SOC 2, GDPR, and HIPAA requirements.

---

## SOC 2 Trust Services Criteria

| Criteria | Requirement | KavachIQ Control | Status |
|----------|------------|-----------------|--------|
| **CC1.1** | Control environment | RBAC roles (Admin/Operator/Viewer), documented security policies | ✅ |
| **CC2.1** | Information & communication | Audit logging, alert notifications, structured logging | ✅ |
| **CC3.1** | Risk assessment | Smart Engine anomaly detection, health scoring | ✅ |
| **CC4.1** | Monitoring | Health checks, anomaly baselines, backup failure alerts | ✅ |
| **CC5.1** | Control activities | Rate limiting, input validation, CORS, error handling | ✅ |
| **CC6.1** | Logical access | JWT authentication, SSO/OIDC, MFA via Entra ID | ✅ |
| **CC6.2** | System access | Password policy, account lockout, refresh token rotation | ✅ |
| **CC6.3** | Role-based access | `require_role()` on every endpoint, 3 role levels | ✅ |
| **CC6.6** | Encryption | AES-256-GCM at rest, TLS 1.2+ in transit | ✅ |
| **CC6.7** | Transmission security | TLS for all API, Graph API, DB, and storage connections | ✅ |
| **CC6.8** | Change management | Git version control, CI/CD pipeline, Terraform IaC | ✅ |
| **CC7.1** | System monitoring | `/health` endpoint, correlation IDs, response time tracking | ✅ |
| **CC7.2** | Incident detection | Anomaly detection, circuit breaker, stale job detector | ✅ |
| **CC7.3** | Incident response | Self-healing retry, alert service, audit trail | ✅ |
| **CC8.1** | Change management | GitHub PRs, CI tests, release quality gate | ✅ |
| **CC9.1** | Risk mitigation | WORM storage, legal hold | ✅ (malware scanning: planned) |

---

## GDPR Compliance

| Article | Requirement | KavachIQ Control | Status |
|---------|------------|-----------------|--------|
| **Art. 5(1)(f)** | Integrity and confidentiality | AES-256-GCM encryption, per-tenant key isolation | ✅ |
| **Art. 17** | Right to erasure | Tenant purge feature, cascade data deletion | ✅ |
| **Art. 25** | Data protection by design | Per-tenant DEK, RBAC, audit logging from day 1 | ✅ |
| **Art. 28** | Processor obligations | Documented security practices, data processing audit trail | ✅ |
| **Art. 30** | Records of processing | Audit log with user, action, timestamp, IP | ✅ |
| **Art. 32** | Security of processing | Encryption, access control, backup validation, resilience | ✅ |
| **Art. 33** | Breach notification | Alert service (email + webhook), anomaly detection | ✅ |
| **Art. 35** | Data protection impact assessment | Security architecture documented, risk assessment via Smart Engine | ✅ |

---

## HIPAA Security Rule

| Safeguard | Standard | KavachIQ Control | Status |
|-----------|----------|-----------------|--------|
| **Administrative** | §164.308(a)(1) | Risk assessment via Smart Engine, security policies documented | ✅ |
| **Administrative** | §164.308(a)(3) | RBAC (Admin/Operator/Viewer), role-based endpoint protection | ✅ |
| **Administrative** | §164.308(a)(4) | Per-tenant data isolation, tenant-scoped access | ✅ |
| **Administrative** | §164.308(a)(5) | Password policy, SSO/MFA support | ✅ |
| **Technical** | §164.312(a)(1) | JWT authentication, SSO/OIDC, MFA | ✅ |
| **Technical** | §164.312(a)(2)(i) | Unique user identification (username + email) | ✅ |
| **Technical** | §164.312(a)(2)(iii) | Refresh token rotation, configurable session timeout | ✅ |
| **Technical** | §164.312(a)(2)(iv) | AES-256-GCM encryption, per-tenant keys | ✅ |
| **Technical** | §164.312(b) | Audit logging (who, what, when, where) | ✅ |
| **Technical** | §164.312(c)(1) | SHA-256 content hashing, backup validation | ✅ |
| **Technical** | §164.312(c)(2) | WORM storage, immutable snapshots | ✅ |
| **Technical** | §164.312(d) | JWT + password verification, SSO identity verification | ✅ |
| **Technical** | §164.312(e)(1) | TLS 1.2+ for all data transmission | ✅ |
| **Physical** | §164.310 | Azure datacenter physical security (SOC 2 Type II certified) | ✅ (Azure) |

---

## DORA (Digital Operational Resilience Act)

| Article | Requirement | KavachIQ Control | Status |
|---------|------------|-----------------|--------|
| **Art. 6** | ICT risk management | Smart Engine risk assessment, anomaly detection | ✅ |
| **Art. 9** | Protection and prevention | WORM storage, encryption, pre-flight validation | ✅ (malware scanning: planned) |
| **Art. 10** | Detection | Anomaly detection, circuit breaker, health monitoring | ✅ |
| **Art. 11** | Response and recovery | Self-healing retry, mass recovery, recovery confidence scoring | ✅ |
| **Art. 12** | Backup policies | Configurable SLA policies, retention, WORM | ✅ |
| **Art. 13** | Learning and evolving | Health baselines, trend analysis, audit trail | ✅ |

---

## Verification

Run `make security-scan` to verify all controls programmatically.

Last verified: March 2026
