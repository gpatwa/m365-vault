# WORM Immutable Storage

## Overview

KavachIQ supports WORM (Write-Once-Read-Many) immutable storage for backup data, ensuring that once a backup is written, it cannot be modified, overwritten, or deleted until the retention period expires. WORM storage is a critical defense against ransomware that targets backup infrastructure and a requirement for several regulatory compliance frameworks.

## What WORM Means

WORM stands for **Write-Once-Read-Many**. Data written to WORM storage can be read any number of times but cannot be altered or deleted. This guarantee is enforced at the storage layer, meaning that even an attacker with administrative credentials cannot destroy backup data protected by a WORM retention lock.

## Enabling WORM on SLA Policies

WORM immutability is configured at the SLA policy level. When creating or editing an SLA policy, set the following:

| Setting | Description |
|---|---|
| `worm_enabled` | Set to `true` to enable WORM protection for all backups governed by this policy. |
| `retention_days` | The minimum number of days backups must be retained before they can be deleted. |

Once enabled, all new backup artifacts created under this policy are written with WORM protection. Existing backups created before WORM was enabled are not retroactively locked.

## Retention Locks

Every WORM-protected backup artifact carries a `locked_until` timestamp calculated at write time:

```
locked_until = backup_timestamp + retention_days
```

Before this timestamp, the artifact cannot be deleted by any operation, including:

- Manual deletion by an administrator
- Automated retention cleanup
- API-initiated delete requests
- Storage-level operations

After the `locked_until` timestamp passes, the artifact becomes eligible for normal retention-based cleanup.

## Legal Hold

Legal hold is a special override that **extends** WORM protection indefinitely, regardless of the original retention period. When a legal hold is placed on a tenant or workload:

- All existing WORM-protected backups are retained indefinitely, even if their `locked_until` date has passed.
- All new backups are created with indefinite retention.
- The legal hold can only be released by an administrator with the appropriate role.

Legal hold is designed for litigation preservation, regulatory investigations, and audit scenarios where data must be retained beyond the standard policy.

## Compliance Use Cases

WORM immutable storage supports compliance with the following regulatory frameworks:

| Regulation | Requirement | How WORM Addresses It |
|---|---|---|
| **HIPAA** | Protected health information must be recoverable and protected from unauthorized destruction. | WORM prevents deletion of backup data containing PHI for the configured retention period. |
| **SEC Rule 17a-4** | Broker-dealers must preserve electronic records in non-rewritable, non-erasable format. | WORM storage meets the non-rewritable, non-erasable requirement for electronic record retention. |
| **SOX (Sarbanes-Oxley)** | Financial records and audit trails must be retained and protected from tampering. | WORM ensures financial data backups cannot be modified or destroyed during the retention window. |
| **GDPR** | Data must be protected against accidental loss, destruction, or damage. | WORM provides protection against unauthorized or accidental deletion of backup data. |

## How WORM Prevents Ransomware from Deleting Backups

A common ransomware escalation tactic is to compromise backup infrastructure and delete or encrypt backup data before encrypting production systems. This eliminates the victim's ability to recover without paying the ransom.

WORM storage breaks this attack chain:

1. The attacker gains access to the backup management layer.
2. The attacker attempts to delete or overwrite backup artifacts.
3. The storage layer rejects the operation because the `locked_until` timestamp has not passed.
4. The backup data remains intact and available for recovery.

Even if the attacker obtains storage credentials, WORM retention locks are enforced at the infrastructure level and cannot be bypassed through the application layer.

## Best Practices

- Enable WORM on all production SLA policies. The storage cost increase is minimal compared to the risk of losing backup data to ransomware.
- Set retention periods to at least 30 days. Shorter periods may not provide sufficient recovery window if an attack is discovered late.
- Use legal hold proactively when your organization receives litigation notices, rather than waiting for a formal preservation order.
- Test restore operations from WORM-protected backups regularly to confirm that immutability does not interfere with the restore workflow.
