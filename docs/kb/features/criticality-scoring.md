# Criticality Scoring

## Overview

Criticality Scoring automatically ranks every user and resource in your Microsoft 365 tenant by business importance. This ranking drives backup prioritization, recovery ordering, and anomaly alert severity, ensuring that your most valuable accounts are protected first and recovered first.

Scores are auto-detected from Microsoft Graph data. No manual configuration, spreadsheet imports, or tagging workflows are required.

## How Scores Are Calculated

Each account receives a composite score from 0 to 100 based on four weighted factors:

| Factor | Weight | What It Evaluates |
|---|---|---|
| **Role Weight** | 40% | Directory roles held by the account. Global Administrator scores highest, followed by Exchange Admin, SharePoint Admin, Security Admin, and so on. Accounts with no admin roles receive a baseline score. |
| **Data Sensitivity** | 30% | Signals from Microsoft Information Protection labels, DLP policy matches, and sensitivity labels applied to the user's mailbox and OneDrive content. Accounts handling confidential or highly confidential data score higher. |
| **Activity Level** | 20% | Sign-in recency and frequency from Entra ID sign-in logs. Accounts active today score higher than accounts dormant for 30+ days. Stale accounts are deprioritized. |
| **Business Dependency** | 10% | Group memberships indicating VIP status, executive distribution lists, or business-critical team membership. Membership in groups tagged as critical increases this factor. |

## Auto-Detection from Microsoft Graph

KavachIQ pulls the following data via Microsoft Graph to compute scores without manual input:

- **Directory role assignments** via `/directoryRoles` and `/roleManagement/directory/roleAssignments`
- **Sensitivity labels** via Information Protection APIs
- **Sign-in activity** via `/auditLogs/signIns`
- **Group memberships** via `/users/{id}/memberOf`
- **Job title and department** via user profile properties

Scores recalculate automatically every 6 hours to reflect organizational changes.

## Tier Classification

Scores map to four tiers that govern backup and recovery behavior:

| Tier | Score Range | Backup Frequency | Recovery Priority |
|---|---|---|---|
| **Critical** | 80--100 | Every 1 hour | Phase 2 (immediately after identity) |
| **High** | 60--79 | Every 4 hours | Phase 3 |
| **Medium** | 30--59 | Every 12 hours | Phase 4 |
| **Low** | 0--29 | Every 24 hours | Phase 4 |

## Worked Example

**CEO (score: 95)**

| Factor | Raw | Weighted |
|---|---|---|
| Role Weight (Global Admin) | 100 | 40 |
| Data Sensitivity (confidential labels) | 90 | 27 |
| Activity Level (active today) | 100 | 20 |
| Business Dependency (VIP group + exec DL) | 80 | 8 |
| **Total** | | **95** |

Result: Critical tier. Backed up hourly. Recovered in Phase 2 of any MVB plan.

**Intern (score: 30)**

| Factor | Raw | Weighted |
|---|---|---|
| Role Weight (no admin roles) | 10 | 4 |
| Data Sensitivity (no labels) | 20 | 6 |
| Activity Level (active this week) | 70 | 14 |
| Business Dependency (no VIP groups) | 10 | 1 |
| **Total** | | **25** |

Result: Low tier. Backed up daily. Recovered in Phase 4.

## Manual Overrides

While scores are fully automatic, administrators can apply manual overrides for specific accounts. Common use cases include boosting the score for a board member who does not hold an admin role, or deprioritizing a service account that inflates activity metrics.

Overrides are preserved across recalculation cycles and are logged in the audit trail.

## Viewing Criticality Scores

Scores are visible on the Users page, sortable and filterable by tier. The Recovery Dashboard uses criticality tiers to order the MVB recovery plan phases.
