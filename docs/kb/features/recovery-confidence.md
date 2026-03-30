# Recovery Confidence Score

## Overview

The Recovery Confidence Score is a composite metric (0--100) that answers the question every IT leader needs answered: **can we actually recover from this backup?** Unlike competitor solutions that report simple backup counts or job success rates, the Recovery Confidence Score validates that your data is restorable, current, and complete.

A high backup count means nothing if those backups are stale, incomplete, or fail during restore. The Recovery Confidence Score closes that gap.

## How the Score Is Calculated

The score is a weighted average of four equally weighted factors (25% each):

| Factor | Weight | What It Measures |
|---|---|---|
| **Backup Freshness** | 25% | How recently the last successful backup completed relative to your RPO target. A backup taken 2 hours ago against a 4-hour RPO scores higher than one taken 3.5 hours ago. |
| **Backup Completeness** | 25% | Percentage of protected items (mailboxes, OneDrive accounts, SharePoint sites, Entra ID objects) that have at least one successful backup within the retention window. |
| **Restore Success Rate** | 25% | Historical ratio of successful restore operations to total restore attempts over the trailing 30-day window. Includes both admin-initiated and automated validation restores. |
| **Validation Pass Rate** | 25% | Percentage of backup artifacts that pass integrity validation, including checksum verification, encryption envelope checks, and decompression tests. |

Each factor produces a sub-score from 0 to 100. The final score is the arithmetic mean of all four.

## Letter Grades

Scores map to letter grades for quick interpretation:

| Grade | Score Range | Meaning |
|---|---|---|
| **A** | 90--100 | Recovery-ready. All factors are healthy. |
| **B** | 75--89 | Generally healthy. One or two factors need attention. |
| **C** | 50--74 | At risk. Multiple factors are degraded. Investigate promptly. |
| **D** | 0--49 | Critical. Recovery capability is severely compromised. Immediate action required. |

## Actionable Recommendations

When any sub-score drops below threshold, Shieldio generates specific recommendations:

- **Low Freshness**: "Backup for Exchange workload is 6 hours behind RPO target. Check connector health and Graph API throttle rates."
- **Low Completeness**: "14 of 312 mailboxes have no backup in the last 7 days. Review excluded accounts and license assignments."
- **Low Restore Success Rate**: "3 of 10 recent restore attempts failed. Review storage connectivity and encryption key availability."
- **Low Validation Rate**: "8% of backup artifacts failed integrity checks. Run a full validation cycle and check for storage corruption."

## How This Differs from Competitor Metrics

Most backup vendors report **job-level metrics**: "backup job succeeded" or "X items backed up." These metrics confirm that data was written to storage but say nothing about whether that data can be read back, decrypted, decompressed, and restored to a working state.

The Recovery Confidence Score is fundamentally different:

- It validates the **full recovery chain**, not just the write path.
- It penalizes **staleness**, not just failure.
- It tracks **completeness** across your entire tenant, catching accounts that silently fall out of protection.
- It incorporates **real restore outcomes**, so a high score means restores actually work.

## Accessing the Score

The Recovery Confidence Score is displayed on the Recovery Dashboard and is available per-workload (Exchange, OneDrive, SharePoint, Entra ID) and as a tenant-wide aggregate. Historical trends are available for the trailing 90 days.

The score refreshes automatically after every backup cycle and after every restore operation.

## API Access

The score is also available via the `/api/v1/recovery-confidence` endpoint for integration with external monitoring and reporting tools. See the API Reference for request and response schema details.
