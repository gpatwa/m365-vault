# Entra ID Backup

## Overview

Shieldio provides comprehensive backup coverage for Microsoft Entra ID (formerly Azure Active Directory), protecting the identity and access configuration that underpins your entire Microsoft 365 environment. Entra ID backup captures 10+ object types, supports incremental delta queries for efficient data transfer, and enables snapshot comparison for configuration drift detection.

## Why Entra ID Backup Is Essential

Your Entra ID configuration is the security foundation of your Microsoft 365 tenant. Conditional access policies enforce MFA requirements, directory roles govern administrative access, and app registrations control third-party integrations. In a compromise scenario, attackers frequently target these configurations first, disabling MFA and conditional access to establish persistent access before moving to data exfiltration.

Without a dedicated Entra ID backup, restoring these configurations after an incident requires manual reconstruction from documentation that may be incomplete, outdated, or nonexistent.

## Object Types Backed Up

Shieldio backs up the following Entra ID object types:

| Object Type | Description | Graph API Source |
|---|---|---|
| **Users** | All user accounts including properties, licenses, and authentication methods | `/users` |
| **Groups + Memberships** | Security groups, Microsoft 365 groups, distribution lists, and their full membership lists | `/groups`, `/groups/{id}/members` |
| **Directory Roles** | Built-in and custom directory role definitions | `/directoryRoles` |
| **Role Assignments** | Which users and groups hold which directory roles | `/roleManagement/directory/roleAssignments` |
| **Conditional Access Policies** | Full policy definitions including conditions, grant controls, and session controls | `/identity/conditionalAccess/policies` |
| **App Registrations** | Application registrations including redirect URIs, API permissions, and certificates | `/applications` |
| **Service Principals** | Enterprise applications and their configurations | `/servicePrincipals` |
| **Named Locations** | IP-based and country-based locations used in conditional access | `/identity/conditionalAccess/namedLocations` |
| **Administrative Units** | Delegated administration boundaries and their members | `/directory/administrativeUnits` |
| **OAuth2 Permission Grants** | Delegated permissions granted to applications on behalf of users | `/oauth2PermissionGrants` |
| **Devices** | Entra ID registered and joined devices | `/devices` |
| **Domains** | Verified domains and their DNS configuration status | `/domains` |

## Why Conditional Access Policy Backup Matters

Conditional access policies are the most critical Entra ID objects to protect. In observed attack patterns:

1. The attacker gains Global Administrator credentials (phishing, token theft, or credential stuffing).
2. The attacker disables or modifies conditional access policies to remove MFA requirements.
3. With MFA disabled, the attacker establishes persistent access via additional compromised accounts or app registrations.
4. Data exfiltration begins only after the security perimeter is weakened.

If you restore mailboxes and files but do not restore the conditional access policies that were in place before the attack, the attacker's modifications remain active. Shieldio's MVB recovery plan restores conditional access policies in Phase 1, before any data restoration begins.

## Delta Query Support

Shieldio uses Microsoft Graph delta queries (`/users/delta`, `/groups/delta`, etc.) for incremental backups. After the initial full snapshot, subsequent backup cycles request only the changes since the last checkpoint. This approach:

- Reduces Graph API call volume by 80--95% for stable tenants
- Minimizes the risk of API throttling
- Decreases backup cycle duration from minutes to seconds for most object types
- Preserves a complete change history for audit and forensic review

Delta tokens are managed automatically. If a delta token expires (tokens are valid for approximately 30 days), Shieldio performs a fresh full sync and establishes a new baseline.

## Snapshot Comparison for Drift Detection

Every Entra ID backup produces a timestamped snapshot. Shieldio compares consecutive snapshots to detect configuration drift, including:

- Conditional access policies that were modified or deleted
- New role assignments granted outside of change management processes
- App registrations with expanded API permissions
- Group membership changes affecting privileged security groups

Drift events appear in the audit timeline and can trigger alerts when changes affect critical security configurations.

## Backup Frequency

Entra ID backups run on the same schedule as your SLA policy, with a recommended minimum frequency of every 4 hours for identity objects. Critical objects such as conditional access policies and role assignments can be backed up as frequently as every hour.
