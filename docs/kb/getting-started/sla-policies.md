# Create SLA Policies

SLA policies define how frequently KavachIQ backs up your data, how long backups are retained, and whether retention locks are enforced. Policies let you apply consistent protection standards across your Microsoft 365 environment.

## What SLA Policies Control

Each SLA policy specifies the following parameters:

| Parameter | Description |
|---|---|
| **Backup frequency** | How often backups run (e.g., every 4 hours, every 12 hours, daily). |
| **Retention period** | How long backup snapshots are kept before automatic expiration (e.g., 30 days, 1 year, 7 years). |
| **Retention lock (WORM)** | When enabled, backups cannot be deleted or modified before the retention period expires. This supports Write Once Read Many compliance requirements. |
| **RPO target** | The recovery point objective defines the maximum acceptable data loss window. KavachIQ alerts you when actual RPO exceeds the target. |

## Example Policies

Below are three commonly used policy templates. You can customize these or create your own.

### Gold Policy (Mission-Critical)

- **Backup frequency**: Every 4 hours
- **Retention**: 7 years
- **Retention lock**: Enabled (WORM)
- **RPO target**: 4 hours
- **Use case**: Executive mailboxes, legal holds, financial data, HIPAA-regulated health records.

### Silver Policy (Standard Business)

- **Backup frequency**: Every 12 hours
- **Retention**: 1 year
- **Retention lock**: Disabled
- **RPO target**: 12 hours
- **Use case**: General employee mailboxes, departmental SharePoint sites, standard Teams channels.

### Bronze Policy (Archival)

- **Backup frequency**: Daily
- **Retention**: 90 days
- **Retention lock**: Disabled
- **RPO target**: 24 hours
- **Use case**: Shared mailboxes, inactive OneDrive accounts, non-critical document libraries.

## Creating a Policy

1. Navigate to **Policies > SLA Policies**.
2. Click **Create Policy**.
3. Enter a policy name and optional description.
4. Set the backup frequency, retention period, and RPO target.
5. Optionally enable **Retention Lock** for immutable backups.
6. Click **Save**.

## Assigning Policies to Objects

You can assign an SLA policy at multiple levels:

- **Individual object**: Assign a policy to a single mailbox, OneDrive account, SharePoint site, or Team.
- **Bulk assignment**: Select multiple objects on the Workloads page and click **Assign Policy** to apply the same policy to all selected items.
- **Workload-level default**: Under **Policies > Defaults**, set a default policy per workload type. Any newly discovered object without an explicit assignment inherits the workload default.

To assign a policy:

1. Navigate to **Workloads** and select the objects you want to protect.
2. Click **Assign Policy** in the toolbar.
3. Select the desired SLA policy from the dropdown.
4. Click **Apply**.

## SLA Violation Alerts

KavachIQ continuously monitors whether each protected object meets its SLA targets. A violation occurs when:

- **RPO breach**: The time since the last successful backup exceeds the policy RPO target.
- **Backup failure**: A scheduled backup job fails and is not resolved within the RPO window.

When a violation is detected:

1. The object is flagged with a warning indicator on the **Workloads** page.
2. An alert is sent via your configured notification channels (email, webhook, or Teams notification).
3. The **SLA Compliance** dashboard updates to reflect the current compliance percentage.

Review violations promptly and check the **Jobs** page for failed backup details.

## Retention Lock Explained

Retention lock provides immutable backup storage that satisfies regulatory requirements including HIPAA, SEC 17a-4, and FINRA.

When retention lock is enabled on a policy:

- Backup snapshots **cannot be deleted** before the retention period expires, by any user or administrator.
- The retention period **cannot be shortened** after the policy is applied.
- The retention lock setting itself **cannot be disabled** once active on a policy. You must create a new policy if you want different settings.

**Important**: Enable retention lock only when you are certain of your retention requirements. This setting is irreversible for the affected policy.

## Modifying Policies

- You can increase the retention period or shorten the backup frequency on any policy at any time.
- Decreasing the retention period is only allowed on policies **without** retention lock enabled.
- Changes apply to all future backups. Existing snapshots follow the retention rules that were in effect when they were created.

## Next Steps

With your SLA policies configured, proceed to [Run Your First Backup](first-backup.md) to start protecting your data.
