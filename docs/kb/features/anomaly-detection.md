# Anomaly Detection

## Overview

KavachIQ's anomaly detection system continuously monitors backup data patterns to identify threats such as ransomware encryption, data exfiltration, and unusual deletion activity. Detection is based on statistical Z-score analysis against rolling baselines, with zero external dependencies. There are no LLM tokens, no third-party threat intelligence feeds, and no cloud-based ML services involved. The system runs on pure math applied to your backup telemetry.

## How Z-Score Baselines Work

For each protected workload and account, KavachIQ maintains a **7-day rolling average** and standard deviation for key metrics including:

- Total backup size (bytes)
- Item count (emails, files, objects)
- Change rate (new, modified, deleted items per cycle)
- Encryption ratio (percentage of items with encrypted content)

Each new backup cycle is compared against the rolling baseline. The **Z-score** measures how many standard deviations the current observation deviates from the mean:

```
Z = (observed_value - rolling_mean) / rolling_standard_deviation
```

A Z-score of 0 means the observation matches the baseline exactly. Higher absolute values indicate increasingly unusual behavior.

## What Is Detected

### Mass Encryption (Ransomware Indicator)

When the encryption ratio spikes dramatically (e.g., 5% of files were encrypted yesterday, 85% are encrypted today), the Z-score for the encryption metric exceeds threshold. This pattern is a strong indicator of ransomware activity encrypting files in OneDrive or SharePoint.

### Data Exfiltration (Size Drop)

A sudden and significant decrease in total backup size or item count suggests bulk deletion or move operations consistent with data exfiltration. The attacker copies data out, then deletes it to cover tracks.

### Unusual Deletions

A spike in the deletion change rate, where the number of items deleted in a single cycle far exceeds the historical norm, triggers an alert. This can indicate either malicious activity or a misconfigured retention policy.

## Severity Levels

| Severity | Z-Score Threshold | Response |
|---|---|---|
| **Normal** | Z < 2.0 | No action. Within expected variation. |
| **Warning** | 2.0 <= Z < 2.5 | Logged for review. Visible in the anomaly timeline. |
| **Elevated** | 2.5 <= Z < 5.0 | Alert generated. Appears on dashboard with recommended investigation steps. |
| **Critical** | Z >= 5.0 | Urgent alert. Backup isolation recommended. Recovery plan activation may be warranted. |

## Health Score

Each tenant and workload has a health score from 0 to 100 that reflects the overall anomaly state. The health score is a weighted composite:

| Component | Weight | Description |
|---|---|---|
| Encryption anomaly | 35% | Deviation in encryption ratio |
| Size anomaly | 25% | Deviation in total backup size |
| Deletion anomaly | 25% | Deviation in deletion rate |
| Pattern consistency | 15% | Stability of backup patterns over time |

A health score of 100 means all metrics are within normal bounds. The score decreases as anomalies are detected, with critical-severity anomalies causing the steepest drops.

## Alert Generation

When a Z-score crosses the elevated or critical threshold, KavachIQ generates an alert containing:

- The affected tenant and workload
- The specific metric that triggered the alert
- The observed value, baseline mean, and Z-score
- A severity classification
- Recommended next steps (e.g., "Review recent file activity in OneDrive for user X")

Alerts appear on the Anomaly Dashboard and can be forwarded to external SIEM or notification systems via webhook.

## Why No External Dependencies

By using statistical baselines computed entirely from your own backup data, the anomaly detection system:

- Has **zero additional cost** beyond the backup infrastructure itself
- Requires **no API keys** for third-party services
- Operates with **no network dependencies** that could be disrupted during an incident
- Produces **no data egress** to external threat intelligence platforms
- Adapts automatically to your organization's unique data patterns rather than relying on generic signatures
