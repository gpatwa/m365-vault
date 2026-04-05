# RPO/RTO Compliance

## Overview

KavachIQ tracks Recovery Point Objective (RPO) and Recovery Time Objective (RTO) compliance on a per-workload basis, giving IT administrators and compliance teams continuous visibility into whether backup and recovery operations meet their defined service level targets.

## Key Definitions

### Recovery Point Objective (RPO)

RPO defines the **maximum acceptable amount of data loss** measured in time. An RPO of 4 hours means your organization can tolerate losing up to 4 hours of data. If the last successful backup was taken 3 hours ago, you are within RPO. If the last backup was taken 6 hours ago, RPO is violated.

RPO is determined by backup frequency. To achieve a 1-hour RPO, backups must run at least every hour.

### Recovery Time Objective (RTO)

RTO defines the **maximum acceptable downtime** from the moment a recovery is initiated to the moment the data is fully restored and accessible. An RTO of 2 hours means a restore operation must complete within 2 hours.

RTO is influenced by data volume, storage throughput, API rate limits, and the number of items being restored.

## Per-Workload Tracking

KavachIQ tracks RPO and RTO independently for each workload:

| Workload | Typical RPO Range | Typical RTO Range |
|---|---|---|
| **Exchange Online** | 1--24 hours | 30 minutes--4 hours |
| **OneDrive for Business** | 1--24 hours | 1--8 hours |
| **SharePoint Online** | 4--24 hours | 1--12 hours |
| **Entra ID** | 1--6 hours | 5--30 minutes |

Targets are configured in your SLA policy and can vary by workload. For example, you might set a 1-hour RPO for Exchange (email is time-sensitive) and a 12-hour RPO for SharePoint archives.

## Compliance Statuses

Each workload is assigned one of three compliance statuses based on current state:

| Status | Condition | Dashboard Indicator |
|---|---|---|
| **Compliant** | Current RPO and last known RTO are within the SLA target. | Green |
| **At Risk** | Current RPO is approaching the target threshold (within 80% of the limit) or recent RTO measurements show degradation. | Yellow |
| **Violated** | Current RPO exceeds the SLA target, or the most recent restore operation exceeded the RTO target. | Red |

## How Worst-Case RPO Is Calculated

The worst-case RPO for a workload is the **longest gap between consecutive successful backups** observed over the trailing measurement window (default: 7 days). This metric accounts for:

- Backup job failures that created gaps in coverage
- API throttling that delayed backup completion
- Maintenance windows or connector downtime

For example, if Exchange backups run every 4 hours but one cycle failed, the worst-case RPO is 8 hours (the gap spanning two cycles). This is reported even if the current RPO is healthy, because it reveals the actual risk exposure.

## SLA-Based Targets

RPO and RTO targets are defined in the SLA policy attached to each tenant. When creating or editing an SLA policy, you specify:

- **RPO target** per workload (in hours)
- **RTO target** per workload (in hours)
- **Measurement window** for worst-case calculations

KavachIQ evaluates compliance continuously, not just at the end of the policy period.

## Accessing RPO/RTO Data

### Recovery Dashboard

The Recovery Dashboard displays current RPO/RTO compliance for all workloads in a summary view. Each workload shows its current status, the time since last successful backup (current RPO), and the last measured restore duration (estimated RTO).

### API Access

RPO/RTO compliance data is available via the `/api/v1/rpo-rto-compliance` endpoint. The response includes per-workload current RPO, worst-case RPO, estimated RTO, compliance status, and the timestamp of the last evaluation.

## Recommendations

- Set RPO targets based on the business impact of data loss for each workload, not a single blanket value.
- Monitor worst-case RPO trends weekly to catch recurring backup gaps before they become SLA violations.
- Use RTO measurements from test restores to validate that your targets are achievable with current infrastructure and API limits.
