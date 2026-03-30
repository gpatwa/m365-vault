# Run Your First Backup

Once your tenant is connected, workloads are discovered, and SLA policies are assigned, you are ready to run your first backup. This article walks through triggering, monitoring, and verifying a backup job.

## How to Trigger a Backup

### Back Up a Single Object

1. Navigate to **Workloads** and select the workload type (e.g., Exchange).
2. Locate the specific object (e.g., a user mailbox) in the list.
3. Click the **Backup** button on that row.
4. Confirm the action in the dialog. The job starts immediately.

### Back Up All Protected Objects

To back up everything that has an SLA policy assigned:

1. Navigate to **Jobs > Backup**.
2. Click **Backup All** in the top-right corner.
3. Optionally filter by workload type if you only want to back up Exchange or SharePoint.
4. Click **Start**. Shieldio queues one job per protected object and processes them in parallel.

### Scheduled Backups

If you have assigned SLA policies, backups run automatically according to the policy schedule. No manual action is required. You can view upcoming scheduled runs on the **Jobs > Scheduled** tab.

## What Happens During a Backup

When a backup job runs, Shieldio executes the following steps:

1. **Data retrieval**: Shieldio reads data from your Microsoft 365 tenant via the Microsoft Graph API. For mailboxes, this includes messages, attachments, calendar items, contacts, and tasks. For OneDrive and SharePoint, this includes files and metadata.

2. **Compression**: Data is compressed using the zstd algorithm with content-aware adaptive compression levels. Text-heavy content (emails, documents) achieves higher compression ratios than binary files (images, videos).

3. **Deduplication**: Shieldio uses SHA-256 content-addressable storage with content-defined chunking for large files. If the same attachment exists in multiple mailboxes, it is stored only once.

4. **Encryption**: All data is encrypted using AES-256-GCM before being written to storage. Each tenant has its own data encryption key, which is itself protected by a master key encryption key.

5. **Storage**: Encrypted backup data is written to your designated storage target.

6. **Verification**: Shieldio computes and stores checksums for every backed-up object to ensure data integrity during future restores.

## Monitoring Progress

### The Jobs Page

Navigate to **Jobs** to view all running, completed, and failed jobs. Each job entry displays:

- **Job ID**: A unique identifier for the job.
- **Object**: The mailbox, site, or team being backed up.
- **Status**: Current state of the job (see below).
- **Started**: When the job began.
- **Duration**: Elapsed time.
- **Items processed**: Number of items (messages, files) backed up.

### Job Statuses

| Status | Meaning |
|---|---|
| **Queued** | The job is waiting to be picked up by a worker. |
| **Running** | The job is actively reading, compressing, and storing data. |
| **Completed** | The job finished successfully. All items were backed up. |
| **Completed with warnings** | The job finished but some items were skipped (e.g., a file was locked by another process). Review the job details for specifics. |
| **Failed** | The job encountered an error and could not complete. Check the error message in the job details. |
| **Cancelled** | The job was manually cancelled by an administrator. |

### Filtering and Searching Jobs

Use the filters on the Jobs page to narrow results:

- Filter by **workload type** (Exchange, OneDrive, SharePoint, Teams, Entra ID).
- Filter by **status** (Running, Completed, Failed).
- Filter by **date range** to see jobs from a specific time period.
- Search by **object name** (e.g., a user's email address).

## Verifying Your First Backup

After the job completes:

1. Confirm the job status is **Completed** on the Jobs page.
2. Navigate to **Workloads**, find the backed-up object, and click on it.
3. The **Backup History** tab shows all available recovery points with timestamps.
4. Verify that the recovery point matches the time you triggered the backup.

## Idempotency and Safe Retries

Shieldio backup jobs are idempotent. If a job fails partway through or you accidentally trigger a duplicate backup:

- Running the same backup again is always safe. Shieldio detects already-backed-up items via checksums and skips them.
- Duplicate runs do not create duplicate data in storage thanks to deduplication.
- There is no risk of data corruption from overlapping or repeated jobs.

If a job fails, simply retry it. Shieldio resumes from where it left off.

## Troubleshooting

### Backup job stays in "Queued" status

- Check the **System Health** page to confirm all workers are online.
- If many jobs are running concurrently, the queue may take a few minutes to process.

### Backup fails with "Insufficient permissions"

- Verify that the tenant connection is still active under **Settings > Tenants**.
- Reconnect the tenant if the OAuth token has expired or permissions were revoked.

### Backup is slower than expected

- Large mailboxes (over 50 GB) or SharePoint sites with thousands of files may take longer on the first full backup. Subsequent incremental backups are significantly faster.
- Microsoft Graph API throttling can slow down large backups. Shieldio handles throttling automatically with retry logic.

## Next Steps

Your data is now protected. Proceed to [Restore Data](restore-data.md) to learn how to recover data when you need it.
