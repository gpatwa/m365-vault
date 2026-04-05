# Discover Your Workloads

After connecting your Microsoft 365 tenant, KavachIQ discovers the workloads and objects available for protection. This article explains how discovery works, what gets discovered, and how to customize the process.

## Supported Workloads

KavachIQ protects five Microsoft 365 workloads:

| Workload | What Gets Discovered | Typical Duration |
|---|---|---|
| **Exchange Online** | Mailboxes (user, shared, room, equipment), distribution lists, mail-enabled groups | ~2 seconds per 100 mailboxes |
| **OneDrive for Business** | User drive inventories, storage consumption, file counts | ~3 seconds per 100 accounts |
| **SharePoint Online** | Site collections, document libraries, lists, page counts | ~5 seconds per 100 sites |
| **Microsoft Teams** | Teams, channels (standard and private), membership, associated SharePoint sites | ~10 seconds per 100 teams |
| **Entra ID** | Users, groups, service principals, app registrations, role assignments | ~2 seconds per 1,000 objects |

Discovery times are approximate and depend on tenant size and Microsoft Graph API throttling.

## Running Discovery

### Automatic Discovery

When you first connect a tenant, KavachIQ runs a full discovery automatically. Subsequent automatic discoveries run on a daily schedule (configurable under **Settings > Discovery Schedule**).

### Manual Discovery

To run discovery on demand:

1. Navigate to **Workloads**.
2. Click **Discover Now** in the top-right corner.
3. Optionally, select specific workloads to discover (see below).

### Workload-Selective Discovery

You do not need to discover all five workloads every time. To limit the scope:

1. Click **Discover Now**.
2. In the discovery dialog, uncheck any workloads you want to skip.
3. Click **Start Discovery**.

This is useful when you have added new SharePoint sites or Teams and want to pick them up without re-scanning the entire tenant.

## What Gets Discovered Per Workload

### Exchange Online

- User mailboxes, shared mailboxes, room mailboxes, and equipment mailboxes.
- Mailbox size and item count.
- Archive mailbox status (enabled/disabled).
- Litigation hold and in-place hold status.

### OneDrive for Business

- Drive owner and UPN (user principal name).
- Total storage used and file count.
- Last activity date.

### SharePoint Online

- Site collection URL, title, and template type.
- Document library count and total storage consumed.
- Site collection administrator.
- Hub site associations.

### Microsoft Teams

- Team display name, visibility (public/private), and member count.
- Standard and private channels.
- Associated SharePoint site URL for file storage.
- Team owner(s).

### Entra ID

- User accounts (including guest accounts) with license and MFA status.
- Security groups and Microsoft 365 groups with membership counts.
- Application registrations and service principals.
- Directory role assignments.

## Understanding Discovery Results

After discovery completes, the **Workloads** page displays a summary:

- **Total objects**: The count of discovered objects across all workloads.
- **New objects**: Items found for the first time since the last discovery.
- **Removed objects**: Items that existed previously but were not found (e.g., deleted mailboxes).
- **Protection status**: Shows how many objects have an SLA policy assigned versus unprotected.

Click any workload category to drill down into individual objects.

## Incremental vs. Full Discovery

- **Full discovery** enumerates all objects from scratch. This runs on initial connection and can be triggered manually.
- **Incremental discovery** uses Microsoft Graph delta queries to detect changes since the last run. Daily scheduled discoveries use this mode for faster execution.

## Troubleshooting

### Discovery returns fewer objects than expected

- Verify that the connected service account has the required Graph API permissions. A missing permission can cause an entire workload to return zero results.
- Check whether Conditional Access policies are blocking the KavachIQ service principal.

### Discovery is slow

- Large tenants (10,000+ users) may experience Graph API throttling. KavachIQ automatically retries throttled requests with exponential backoff. Allow up to 30 minutes for very large tenants.

### A specific mailbox or site is missing

- Confirm that the object exists and is not soft-deleted in the Microsoft 365 admin center.
- Run a targeted discovery for the specific workload to pick up recent changes.

## Next Steps

Once your workloads are discovered, proceed to [Create SLA Policies](sla-policies.md) to define backup frequency and retention rules.
