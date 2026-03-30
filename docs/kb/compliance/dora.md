# DORA Compliance with Shieldio

The Digital Operational Resilience Act (DORA) establishes requirements for ICT risk management in the European financial sector. Effective January 2025, DORA applies to banks, insurance companies, investment firms, and their critical ICT third-party service providers. This article maps DORA's key articles to Shieldio's controls for Microsoft 365 data protection.

## Article Mapping

### Article 6 -- ICT Risk Management Framework

**Requirement**: Financial entities must implement a comprehensive ICT risk management framework that identifies, protects, detects, responds to, and recovers from ICT-related incidents.

**Shieldio Controls**:
- Smart Engine continuously monitors backup health, object counts, data volumes, and change rates.
- Baseline analysis establishes normal patterns for each tenant, enabling deviation detection.
- Recovery Confidence Score quantifies recoverability, providing a measurable risk metric.
- Dashboard surfaces risk indicators across all protected workloads in a single view.

### Article 9 -- Protection and Prevention

**Requirement**: Financial entities must implement ICT security tools and policies to minimize the impact of ICT risk.

**Shieldio Controls**:
- AES-256-GCM encryption with per-tenant DEKs and per-snapshot key rotation.
- WORM (Write Once Read Many) storage on Enterprise tier prevents backup tampering or deletion, even by administrators.
- SHA-256 integrity hashing ensures backup data has not been altered.
- RBAC with least-privilege defaults limits who can access or modify backup data.

### Article 10 -- Detection

**Requirement**: Financial entities must implement mechanisms to promptly detect anomalous activities.

**Shieldio Controls**:
- Anomaly detection alerts when backup patterns deviate from baselines (e.g., sudden increase in deleted objects, unexpected volume changes).
- Circuit breaker pattern detects cascading failures in Microsoft Graph API calls and halts requests before they propagate.
- Health check endpoints enable continuous monitoring integration with SOC tools.

### Article 11 -- Response and Recovery

**Requirement**: Financial entities must implement ICT business continuity policies and disaster recovery plans with defined RPO and RTO.

**Shieldio Controls**:
- Self-healing retry with exponential backoff (5/15/45 minute intervals) automatically recovers from transient failures.
- Mass recovery capability restores entire workloads (all mailboxes, all sites) from a single operation.
- Granular recovery restores individual items without affecting the broader environment.
- RPO/RTO tracking via the SLA engine provides documented evidence of recovery capability.

### Article 12 -- Backup Policies

**Requirement**: Financial entities must define backup policies specifying scope, frequency, retention, and recovery procedures.

**Shieldio Controls**:
- SLA engine allows defining backup frequency (hourly, daily, weekly) per workload.
- Configurable retention periods from 30 days to 7 years.
- Per-workload backup policies (Exchange, OneDrive, SharePoint, Teams, Entra ID) with independent schedules.
- Recovery Confidence Score validates that backup policies produce recoverable data.

### Article 13 -- Learning and Evolving

**Requirement**: Financial entities must learn from ICT incidents and testing to improve resilience.

**Shieldio Controls**:
- Baseline trend analysis tracks backup health metrics over time, identifying gradual degradation.
- Historical job data enables comparison of backup performance across periods.
- Anomaly detection thresholds automatically adjust as baselines evolve.
- Audit log provides complete history for post-incident review and root cause analysis.

## DORA Reporting Support

Financial entities must report major ICT incidents to regulators. Shieldio supports this process by providing:

| Reporting Need | Shieldio Feature |
|---|---|
| Incident timeline | Audit log with correlation IDs and timestamps |
| Impact assessment | Backup failure reports with affected object counts |
| Recovery evidence | Recovery Confidence Score and restore job reports |
| Root cause data | End-to-end correlation ID tracing |
| Prevention measures | Anomaly detection configuration and baseline reports |

## Third-Party Risk (Article 28)

If your organization classifies Shieldio as a critical ICT third-party provider under DORA, the following information supports your due diligence:

- **Data location**: Backup data resides in your chosen Azure region. No cross-region transfer without explicit configuration.
- **Encryption**: Per-tenant key isolation means Shieldio cannot access your backup data without your encryption keys.
- **Audit access**: Full audit log export is available for your compliance team and regulators.
- **Exit strategy**: Tenant export functionality allows you to retrieve all backup data in standard formats.

## Disclaimer

This document maps DORA articles to Shieldio's technical capabilities. It does not constitute legal or regulatory advice. Consult qualified legal counsel familiar with DORA to assess your specific obligations.
