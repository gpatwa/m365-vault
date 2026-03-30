# Diagnostics Dashboard

## Overview

The Diagnostics Dashboard provides real-time visibility into the health of your Shieldio deployment, including infrastructure checks, Microsoft Graph API performance, backup and restore throughput, and system resilience status. Use this dashboard as your first stop when troubleshooting issues, before filing a support ticket.

## Seven Health Checks

The dashboard runs seven automated health checks and displays a pass/fail status for each:

| Check | What It Validates |
|---|---|
| **Secret Key** | Confirms that the application secret key is configured and valid. A failure here prevents session management and CSRF protection from functioning. |
| **Encryption Key** | Validates that the master Key Encryption Key (KEK) is accessible and can decrypt a test data encryption key (DEK). Failure means backups cannot be encrypted or decrypted. |
| **Connector Configuration** | Verifies that at least one Microsoft Graph connector is configured with a tenant ID, client ID, and client secret. |
| **Connector Secret Test** | Performs a live authentication attempt against Microsoft Entra ID using the configured connector credentials. Catches expired secrets, revoked app registrations, and consent issues. |
| **Database** | Confirms connectivity to the PostgreSQL database and verifies that migrations are current. |
| **Storage** | Tests read and write access to the configured backup storage layer (Azure Blob Storage in production, local filesystem or MinIO in development). |
| **CORS** | Validates that the CORS configuration allows the frontend origin to communicate with the backend API. Catches misconfigured allowed origins after deployment changes. |

Each check displays its status (pass, fail, or warning), the last execution time, and a diagnostic message explaining any failure.

## Graph API Metrics

The Diagnostics Dashboard tracks Microsoft Graph API usage per tenant:

| Metric | Description |
|---|---|
| **Call Volume** | Total Graph API requests in the current measurement window (hourly, daily). Helps identify unexpected spikes that could indicate runaway backup jobs or misconfiguration. |
| **Throttle Rate** | Percentage of Graph API requests that received HTTP 429 (Too Many Requests) responses. A rising throttle rate indicates that backup frequency or parallelism should be reduced. |
| **Average Latency** | Mean response time for Graph API requests in milliseconds. Elevated latency may indicate Microsoft service degradation or network issues. |
| **Error Rate** | Percentage of requests returning 5xx server errors. Persistent errors suggest a Microsoft service issue or a problem with the app registration permissions. |

These metrics help distinguish between Shieldio-side issues and Microsoft-side issues when diagnosing backup failures.

## Performance Metrics

| Metric | Description |
|---|---|
| **Backup Throughput** | Items processed per second and megabytes per second during the most recent backup cycle, broken down by workload. Use this to identify bottlenecks in specific workloads. |
| **Restore Duration** | Time elapsed for the most recent restore operations, broken down by workload and data volume. Feeds into RTO compliance calculations. |
| **Compression Ratio** | Average compression ratio achieved by the zstd compression layer. Indicates storage efficiency. |
| **Deduplication Savings** | Percentage of data eliminated by content-addressable deduplication. Higher values mean less storage consumed. |

## Circuit Breaker Status

Shieldio implements circuit breakers on external service calls (Graph API, storage, database) to prevent cascading failures. The dashboard displays the current state of each circuit breaker:

| State | Meaning |
|---|---|
| **Closed** | Normal operation. Requests flow through without restriction. |
| **Open** | The failure threshold has been exceeded. Requests are blocked to allow the downstream service to recover. The dashboard shows when the circuit will attempt to close. |
| **Half-Open** | The circuit is testing whether the downstream service has recovered by allowing a limited number of requests through. |

## Resilience Overview

The resilience section aggregates circuit breaker states, retry counts, and fallback activations into a single view. It shows:

- How many retries were executed in the current window
- Whether any fallback mechanisms were activated
- The overall system resilience status (healthy, degraded, or impaired)

## Troubleshooting Workflow

Before filing a support ticket, use the Diagnostics Dashboard to gather context:

1. **Check the seven health checks.** If any check fails, the diagnostic message explains the root cause and remediation steps.
2. **Review Graph API metrics.** If throttle rate is elevated, reduce backup parallelism or increase the interval between cycles.
3. **Inspect circuit breaker states.** An open circuit breaker indicates a downstream service outage. Wait for the half-open test or investigate the external service.
4. **Review performance metrics.** If backup throughput has dropped, check storage connectivity and Graph API latency.
5. **Export diagnostics.** The dashboard provides an export function that generates a diagnostic report suitable for attaching to a support ticket.

This workflow resolves the majority of common issues without requiring support team involvement.
