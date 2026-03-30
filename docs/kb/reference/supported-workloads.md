# Supported Workloads

Shieldio protects data across five Microsoft 365 workloads. This article details the specific object types, backup methods, and capabilities for each workload.

## Coverage Matrix

| Workload | Object Types | Backup Method | Key Capabilities |
|---|---|---|---|
| Exchange Online | Emails, calendar events, contacts, attachments | Delta query, per-folder | Incremental sync, attachment preservation, folder hierarchy |
| OneDrive for Business | Files, folders, version history | Delta query, content download | Incremental sync, file versioning, folder structure |
| SharePoint Online | Sites, document libraries, lists, list items | Multi-drive delta, list expansion | Site-level and library-level backup, list schema + data |
| Microsoft Teams | Channel messages, files, 1:1 chats, group chats, team settings | Export API, file download | Message threading, reactions, file attachments |
| Entra ID (Azure AD) | 10+ directory object types | Graph API snapshot | Full directory backup for disaster recovery |

## Exchange Online

### What Is Backed Up

- **Emails**: Full message body, headers, read/unread status, categories, and flags.
- **Calendar events**: Event details, attendees, recurrence patterns, and attachments.
- **Contacts**: All contact fields including custom properties.
- **Attachments**: Inline and file attachments are stored alongside their parent message.

### Backup Method

Shieldio uses Microsoft Graph delta queries on a per-folder basis. On the first run, a full sync captures all items. Subsequent runs retrieve only new, modified, or deleted items since the last sync, minimizing API calls and processing time.

### Restore Capabilities

- Restore individual emails, events, or contacts to the original or a different mailbox.
- Restore entire folders with hierarchy preserved.
- Full mailbox restore to a point in time.

## OneDrive for Business

### What Is Backed Up

- **Files**: Full file content for all supported file types.
- **Folders**: Complete folder hierarchy and structure.
- **Version history**: All available file versions at the time of backup.

### Backup Method

Delta queries track changes at the drive level. File content is downloaded and encrypted before storage. Large files are handled via chunked download to avoid timeouts.

### Restore Capabilities

- Restore individual files or folders to the original or a different OneDrive.
- Restore a specific version of a file.
- Full drive restore to a point in time.

## SharePoint Online

### What Is Backed Up

- **Sites**: Site metadata and configuration.
- **Document libraries**: All files and folders within each document library on the site.
- **Lists**: List schema (columns, content types, views) and all list items.
- **List items**: Field values, attachments, and metadata for each item.

### Backup Method

Shieldio uses multi-drive delta queries to track changes across all document libraries on a site. Lists are expanded separately, backing up both schema and item data.

### Restore Capabilities

- Restore individual documents or list items.
- Restore entire document libraries or lists with schema.
- Full site restore including all libraries and lists.

## Microsoft Teams

### What Is Backed Up

- **Channel messages**: Full message content, threading (replies), reactions, mentions, and inline images.
- **Files**: Files shared in channels (stored in the team's SharePoint site).
- **1:1 chats**: Direct messages between two users, including attachments and reactions.
- **Group chats**: Multi-person chat threads with full message history.
- **Team settings**: Team name, description, member list, channel configuration, and tabs.

### Backup Method

Channel messages and chats are retrieved via the Microsoft Teams Export API. Files associated with teams are backed up through the underlying SharePoint document library using delta queries.

### Restore Capabilities

- Restore channel messages to the original or a new channel.
- Restore individual chat messages.
- Restore team files via the SharePoint restore path.
- Export messages to standard formats for compliance review.

### Important Notes

- Teams Export API access requires a Microsoft 365 E5 license or the Microsoft Teams Export API add-on.
- Chat backup requires application-level consent from an Azure AD Global Administrator.

## Entra ID (Azure AD)

### What Is Backed Up

Shieldio backs up 10+ Entra ID object types:

| Object Type | Description |
|---|---|
| Users | All user properties, including custom attributes and extension properties |
| Groups | Security groups, Microsoft 365 groups, and distribution lists with membership |
| Directory roles | Role definitions and role assignments |
| Conditional Access policies | Full policy configuration including conditions and grant controls |
| App registrations | Application properties, redirect URIs, and API permissions |
| Service principals | Enterprise application configurations |
| Named locations | IP-based and country-based location definitions |
| Administrative units | AU definitions and member assignments |
| OAuth2 permission grants | Delegated permission consents |
| Devices | Device registrations and compliance state |
| Domains | Verified domain configurations |

### Backup Method

Entra ID objects are retrieved via Microsoft Graph API snapshot queries. Each backup captures the full state of all configured object types.

### Restore Capabilities

- Restore individual objects (e.g., a deleted Conditional Access policy).
- Compare current state against a backup snapshot to identify drift.
- Full directory restore for disaster recovery scenarios.

### Important Notes

- Entra ID backup requires Directory.Read.All permission at minimum.
- Restoring Conditional Access policies or role assignments requires additional write permissions.
- Password hashes and MFA registration data are not accessible via Graph API and cannot be backed up.

## Workload Availability by Tier

| Workload | Community | Professional | Business | Enterprise |
|---|---|---|---|---|
| Exchange Online | Yes | Yes | Yes | Yes |
| OneDrive | Yes | Yes | Yes | Yes |
| SharePoint | Yes | Yes | Yes | Yes |
| Teams | -- | Yes | Yes | Yes |
| Entra ID | -- | Yes | Yes | Yes |

Community tier supports up to 3 workloads and 25 objects. See [Pricing](/docs/kb/reference/pricing.md) for full tier details.
