# Understanding Graph API Throttling

Microsoft Graph API enforces per-tenant rate limits to protect service health. When your backup jobs trigger these limits, Microsoft returns HTTP 429 (Too Many Requests). This article explains why throttling happens, how Shieldio handles it, and what you can do if it persists.

## Why Microsoft Throttles Requests

Microsoft applies throttling at multiple levels:

- **Per-app, per-tenant**: Each registered application has a request budget per tenant. Backup workloads that enumerate thousands of mailboxes or files can exhaust this budget quickly.
- **Per-resource**: Individual mailboxes, sites, and drives have their own sub-limits. A single large mailbox can trigger throttling independently.
- **Service-level**: During periods of high global load, Microsoft may apply broader throttling across all tenants.

Throttling is normal during large backup operations. It does not indicate a misconfiguration.

## How Shieldio Handles Throttling

Shieldio's backup engine includes three layers of throttling mitigation:

### 1. Exponential Backoff with Jitter

When a 429 response is received, Shieldio waits for the duration specified in the `Retry-After` header. If no header is present, it applies exponential backoff starting at 5 seconds, doubling on each retry, with random jitter to prevent synchronized retries across workers.

### 2. Adaptive Concurrency Reduction

The engine automatically reduces the number of parallel Graph API requests when throttling is detected. Concurrency drops in steps (e.g., from 10 parallel requests down to 5, then 2) and gradually recovers once throttling stops.

### 3. Circuit Breaker

If a specific resource (mailbox, site, drive) returns repeated 429 responses, the circuit breaker temporarily suspends requests to that resource. Other resources continue processing. The circuit resets after a cooldown period and retries the suspended resource.

## Error Code E3001

Throttling events surface as error code **E3001** in job logs and the API. The error detail includes the specific resource that was throttled and the retry schedule.

```json
{
  "code": "E3001",
  "message": "Graph API throttled",
  "detail": "429 received for GET /users/user@contoso.com/messages (Retry-After: 30s)",
  "fix": "No action required. Automatic retry scheduled.",
  "correlation_id": "abc123-def456"
}
```

E3001 events are informational during normal operation. The backup job continues processing other objects and returns to the throttled resource automatically.

## What to Do If Throttling Persists

If backup jobs consistently fail to complete due to throttling:

1. **Stagger backup schedules**: Avoid running backups for all workloads at the same time. Spread Exchange, OneDrive, and SharePoint jobs across different windows.
2. **Reduce scope**: Back up high-priority mailboxes and sites first, then run a second pass for the remainder.
3. **Check other applications**: Other apps registered in the same Azure AD tenant share the same rate budget. Verify that migration tools, monitoring agents, or other integrations are not consuming the quota.
4. **Review Microsoft service health**: Visit [status.office.com](https://status.office.com) to check for active incidents that may cause elevated throttling.
5. **Contact support**: If throttling prevents backup completion across multiple consecutive windows, open a support ticket with the job correlation IDs. The team can help tune concurrency settings for your environment.

## Further Reading

- [Microsoft Graph throttling guidance](https://learn.microsoft.com/en-us/graph/throttling) -- Official documentation on Graph API rate limits, best practices, and Retry-After handling.
- [Error Code Reference](/docs/kb/troubleshooting/error-codes.md) -- Full list of Shieldio error codes.
