# Resolving Backup Failures

Backup jobs process thousands of objects across mailboxes, drives, and sites. Individual items can fail without causing the entire job to fail. This article explains failure categories, automatic retry behavior, and how to investigate and resolve persistent failures.

## Failure Categories

Each failed item is tagged with one of the following error categories:

| Category | Description | Auto-Retry |
|---|---|---|
| `permission_denied` | Graph API returned 403. The app lacks permission for this resource. | No |
| `not_found` | The item was deleted or moved between discovery and backup. | No |
| `throttled` | Microsoft returned 429. See [Graph Throttling](/docs/kb/troubleshooting/graph-throttling.md). | Yes |
| `timeout` | The Graph API call exceeded the 120-second deadline. | Yes |
| `quota_exceeded` | The tenant or mailbox has exceeded its Microsoft storage quota. | No |
| `file_too_large` | The file exceeds the maximum supported size (250 MB per item). | No |
| `encryption_error` | The item could not be encrypted before storage. Typically indicates a key management issue. | No |
| `storage_error` | The backup payload could not be written to the storage backend. | Yes |
| `invalid_data` | The Graph API returned data that could not be parsed or validated. | No |
| `auth_expired` | The OAuth token expired mid-job and could not be refreshed. | Yes |
| `server_error` | Graph API returned 500/502/503. Microsoft-side transient error. | Yes |
| `network_error` | Connection to Graph API was lost during transfer. | Yes |
| `unknown` | An unexpected error occurred. The raw error is logged for investigation. | Yes |

## Automatic Retry Behavior

Items tagged for auto-retry follow a three-attempt schedule:

| Attempt | Delay After Failure |
|---|---|
| 1st retry | 5 minutes |
| 2nd retry | 15 minutes |
| 3rd retry | 45 minutes |

If all three retries fail, the item is marked as permanently failed for that job run. It will be retried in the next scheduled backup window.

## Viewing Failed Items

### Dashboard

1. Navigate to **Jobs** in the sidebar.
2. Select the completed backup job.
3. Click the **Failed Items** tab.
4. Use the category filter to narrow results (e.g., show only `permission_denied`).

### API

```
GET /api/backup/jobs/{job_id}/failures?category=throttled&page=1&page_size=50
```

The response includes the object ID, error category, error detail, retry count, and the timestamp of the last attempt.

## Manual Retry

To retry all failed items from a completed job:

- **Dashboard**: Open the job, click **Retry Failed Items**.
- **API**: `POST /api/backup/jobs/{job_id}/retry`

Manual retry creates a new child job that processes only the previously failed items. It follows the same retry schedule described above.

## Resolving Persistent Failures

### permission_denied

Verify that admin consent has been granted for all required Graph API permissions. See [Fixing Connection Failures](/docs/kb/troubleshooting/connection-failures.md) (E1003). Some resources, such as shared mailboxes or restricted sites, may require additional permissions.

### not_found

This is expected when users delete items between backup discovery and data transfer. No action is needed. The item will not appear in future jobs.

### quota_exceeded

The Microsoft 365 mailbox or OneDrive has hit its storage limit. This is a tenant-side issue. Ask the Microsoft 365 administrator to increase the quota or archive old data.

### file_too_large

Files over 250 MB are skipped. If you need to protect these files, contact support to discuss chunked backup options.

### encryption_error

Check that the encryption key configuration is valid. Navigate to **Settings > Security** and verify the key status. If the key has been rotated, ensure the previous key is still available for decryption of existing snapshots.

## When to Contact Support

Open a support ticket if:

- More than 10% of items fail consistently across multiple job runs.
- `encryption_error` or `storage_error` failures appear and do not resolve after checking configuration.
- `unknown` category errors appear repeatedly for the same objects.

Always include the job ID and correlation IDs from the failed items.
