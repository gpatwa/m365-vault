# Restore Data

When data loss occurs, whether from accidental deletion, a departing employee, or a ransomware incident, Shieldio provides multiple restore options to get your organization back to normal quickly.

## Restore Types

Shieldio supports five restore methods to cover different recovery scenarios:

| Restore Type | Description | Use Case |
|---|---|---|
| **Full in-place restore** | Restores all data back to the original mailbox, OneDrive, or SharePoint site. | Recover from bulk deletion or corruption. |
| **Item-level restore** | Restores individual items (a single email, file, or calendar event) to the original location. | Recover a specific accidentally deleted item. |
| **Cross-user restore** | Restores data to a different user or location than the original. | Recover a former employee's data into a manager's mailbox or a shared mailbox. |
| **Export** | Downloads backup data as a file (PST for Exchange, ZIP for OneDrive/SharePoint). | Provide data to legal counsel, auditors, or external parties. |
| **Mass recovery** | Restores multiple objects simultaneously across your tenant. | Recover from ransomware that affected dozens or hundreds of accounts. |

## How to Restore from the UI

### Step 1: Select the Object

1. Navigate to **Workloads** and locate the object you want to restore (mailbox, OneDrive account, SharePoint site, or Team).
2. Click on the object to open its detail view.
3. Select the **Backup History** tab.

### Step 2: Choose a Recovery Point

Shieldio displays all available recovery points with timestamps. You can:

- **Browse the timeline**: Scroll through recovery points to find the exact point in time you need.
- **Search by date**: Use the date picker to jump to a specific day.
- **Preview contents**: Click on a recovery point to see the items it contains before committing to a restore. This lets you verify you have selected the right point in time.

### Step 3: Select the Restore Type

1. Click **Restore** on your chosen recovery point.
2. Select the restore type from the options presented:
   - **In-place**: Restores to the original location.
   - **Item-level**: Lets you browse and select individual items to restore.
   - **Cross-user**: Prompts you to specify a target user or location.
   - **Export**: Generates a downloadable file.
3. Configure any additional options (see below).
4. Click **Start Restore**.

### Restore Options

- **Overwrite existing items**: Choose whether to overwrite items that already exist at the target location or skip them.
- **Restore to subfolder**: Optionally restore into a designated subfolder (e.g., "Restored Items") to avoid mixing restored data with current data.
- **Include permissions**: For SharePoint and OneDrive restores, choose whether to restore the original sharing permissions or inherit permissions from the target location.

## Point-in-Time Selection

Shieldio keeps every backup snapshot according to your SLA policy retention period. This means you can restore to any point in time for which a backup exists.

For example, if your policy backs up every 4 hours with 1-year retention, you have up to 2,190 recovery points per object to choose from.

When selecting a recovery point, consider:

- **Before the incident**: Choose the most recent backup taken before the data loss event.
- **Specific date/time**: Use the date picker if you know exactly when the incident occurred.
- **Compare snapshots**: Preview the contents of multiple recovery points to identify the best one.

## Restore Verification

After a restore completes, Shieldio provides verification details:

- **Item count**: Number of items restored versus total items in the recovery point.
- **Integrity check**: Confirmation that all restored items passed checksum verification.
- **Restore log**: A detailed log of every item restored, including any items that were skipped or encountered errors.

Review the restore job on the **Jobs** page. The status shows **Completed** when all items are successfully restored, or **Completed with warnings** if some items required attention.

We recommend spot-checking a few restored items in Microsoft 365 to confirm they appear correctly.

## Mass Recovery for Ransomware Scenarios

When ransomware or a widespread attack affects multiple accounts, Shieldio's mass recovery feature enables rapid tenant-wide restoration.

### How to Perform Mass Recovery

1. Navigate to **Jobs > Restore**.
2. Click **Mass Recovery**.
3. Select the affected workload type or choose **All Workloads**.
4. Choose a recovery point strategy:
   - **Last known good**: Shieldio automatically selects the most recent backup before the incident timestamp you specify.
   - **Specific date/time**: Manually choose a single recovery point for all objects.
5. Review the list of objects that will be restored and the selected recovery points.
6. Click **Start Mass Recovery**.

### Mass Recovery Considerations

- Mass recovery jobs are processed in parallel to minimize total recovery time.
- Progress is tracked per object on the Jobs page, giving you visibility into the overall recovery status.
- You can pause or cancel a mass recovery if needed. Objects already restored are not affected by cancellation.
- For large-scale recovery (hundreds of accounts), plan for Microsoft Graph API write throttling. Shieldio manages throttling automatically, but full tenant recovery may take several hours depending on data volume.

## Troubleshooting

### Restore fails with "Target not found"

- The original mailbox or site may have been permanently deleted. Use the **Cross-user** restore option to redirect the data to an active location.

### Restored items are missing attachments

- Verify you selected the correct recovery point. Preview the backup contents to confirm attachments are present before retrying.

### Export download is slow

- Large exports (over 10 GB) may take time to generate. The download link remains available on the Jobs page for 72 hours after generation.

## Next Steps

You now know how to protect and restore your Microsoft 365 data with Shieldio. For additional topics, explore the Shieldio knowledge base or contact support at **support@shieldio.com**.
