# Microsoft 365 Shared Responsibility Model

Many organizations assume that Microsoft fully protects their data in Microsoft 365. In reality, Microsoft operates under a shared responsibility model where infrastructure availability is their responsibility, but data protection is yours. This article clarifies the boundary and explains why third-party backup is essential.

## What Microsoft Protects

Microsoft is responsible for:

- **Infrastructure availability**: Keeping Exchange Online, SharePoint Online, OneDrive, and Teams services running.
- **Geo-redundant replication**: Replicating data across datacenters within a region for hardware failure resilience.
- **Physical security**: Securing datacenters against physical threats.
- **Platform patching**: Keeping the underlying platform updated and secure.
- **Basic data redundancy**: Short-term protection against datacenter-level failures.

These protections ensure the service stays online. They do not protect your data from loss, corruption, or unauthorized changes.

## What You Must Protect

Your organization is responsible for:

- **Backup and long-term retention**: Microsoft does not provide point-in-time backup. Their recycle bin and retention policies are not backup.
- **Ransomware recovery**: If ransomware encrypts files synced to OneDrive or SharePoint, Microsoft's versioning has limits. A verified backup with integrity checking is the only reliable recovery path.
- **Accidental and malicious deletion recovery**: The recycle bin retains items for up to 93 days. After that, data is permanently gone. Intentional deletion by a malicious insider bypasses recycle bin protections entirely.
- **Compliance and legal hold**: Regulatory requirements (HIPAA, SOC 2, GDPR, DORA) often mandate independent backup copies with defined retention periods. Native Microsoft retention policies may not satisfy auditors.
- **Departure and offboarding**: When employees leave and licenses are removed, their mailbox and OneDrive data can be deleted after 30 days. Without backup, that data is lost.
- **Compliance evidence**: Demonstrating that you can recover data to a specific point in time is a requirement for many compliance frameworks.

## The 93-Day Recycle Bin Is Not Backup

Microsoft 365's recycle bin is a convenience feature, not a data protection solution:

| Capability | Recycle Bin | Third-Party Backup |
|---|---|---|
| Retention period | Up to 93 days | Configurable (30 days to 7+ years) |
| Point-in-time restore | No | Yes |
| Ransomware protection | Limited (versioning only) | Full (immutable snapshots) |
| Malicious deletion protection | No (admin can purge) | Yes (WORM storage option) |
| Independent from Microsoft | No | Yes |
| Compliance evidence | Insufficient for most frameworks | Audit log + RCS reports |
| Granular restore | Limited | Item-level, folder-level, full workload |

## Why Third-Party Backup Is Essential

Microsoft's own documentation acknowledges the shared responsibility model. The service-level agreement guarantees uptime, not data recoverability. Consider these scenarios:

1. **An admin accidentally deletes a shared mailbox** -- Recoverable from recycle bin within 30 days. After that, the data is permanently lost without backup.
2. **Ransomware encrypts files across OneDrive accounts** -- OneDrive versioning can help, but only if detected quickly and if version history limits have not been exceeded.
3. **A departing employee deletes their files before offboarding** -- If the deletion is not noticed before license removal, the data is gone.
4. **A regulatory audit requires data from 18 months ago** -- Native retention policies may not have been configured to retain that data. A backup with configurable retention ensures availability.
5. **A compliance framework requires proof of recoverability** -- Auditors want evidence that you can restore data, not just that it exists somewhere.

## How KavachIQ Addresses the Gap

KavachIQ provides the data protection layer that sits on top of Microsoft's infrastructure:

| Responsibility | Solution |
|---|---|
| Point-in-time backup | Automated snapshots with delta tracking |
| Long-term retention | Configurable policies up to 7 years |
| Ransomware recovery | Immutable snapshots with integrity verification |
| Compliance evidence | Audit log, Recovery Confidence Score, exportable reports |
| Accidental deletion | Granular restore of individual items from any snapshot |
| Encryption | AES-256-GCM with per-tenant keys, independent of Microsoft |

## Further Reading

- [Microsoft Shared Responsibility Model](https://learn.microsoft.com/en-us/azure/security/fundamentals/shared-responsibility) -- Microsoft's official documentation on shared responsibility in cloud services.
- [Supported Workloads](/docs/kb/reference/supported-workloads.md) -- What KavachIQ backs up across Microsoft 365.
