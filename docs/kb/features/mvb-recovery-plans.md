# MVB Recovery Plans

## Overview

An MVB (Minimum Viable Business) Recovery Plan is a structured, prioritized playbook that defines the order in which Microsoft 365 resources must be restored to bring your organization back to operational status as fast as possible. MVB plans are auto-generated from your organizational context and follow NIST incident recovery guidelines.

The core principle: restore the resources that matter most first, in the order that prevents re-compromise.

## Why MVB Matters

During a ransomware incident or catastrophic data loss, restoring everything simultaneously is neither possible nor advisable. A flat restore queue treats the CEO's mailbox the same as a test account and ignores critical dependencies between identity controls and data access.

MVB plans solve this by defining a phased recovery sequence driven by criticality scores and security dependencies.

## The Four Recovery Phases

MVB plans follow a strict four-phase sequence aligned with NIST SP 800-184 guidance:

### Phase 1: Identity Controls

**What is restored:** Entra ID objects including conditional access policies, directory roles, role assignments, named locations, and multi-factor authentication configurations.

**Why identity restores first:** In most compromise scenarios, attackers disable conditional access policies and MFA before exfiltrating data. If you restore mailboxes before restoring identity controls, the attacker's persistence mechanisms remain active and the restored data is immediately re-compromised. Phase 1 re-establishes the security perimeter before any data flows back in.

**Typical duration:** 5--15 minutes.

### Phase 2: Critical Users

**What is restored:** Mailboxes, OneDrive accounts, and SharePoint sites belonging to users in the Critical tier (criticality score 80--100). This typically includes C-suite executives, Global Administrators, and accounts handling highly sensitive data.

**Why these users are next:** These accounts hold the highest-value data and the broadest access permissions. Restoring them immediately after identity controls gives leadership operational capability while the broader restore continues.

**Typical duration:** 15--60 minutes depending on data volume.

### Phase 3: High Priority Users

**What is restored:** Resources belonging to users in the High tier (criticality score 60--79). This typically includes department heads, senior engineers, finance team members, and other roles with elevated access or sensitive data.

**Typical duration:** 1--4 hours depending on data volume.

### Phase 4: Full Recovery

**What is restored:** All remaining resources including Medium and Low tier users, shared mailboxes, archived content, and non-critical SharePoint sites.

**Typical duration:** 4--24 hours depending on total tenant size.

## Auto-Generation

MVB plans are generated automatically based on:

- **Criticality scores** for user and resource classification into tiers
- **Entra ID object inventory** for Phase 1 sequencing
- **Workload dependencies** to ensure SharePoint site collections restore before dependent subsites
- **Data volume estimates** for duration projections per phase

No manual configuration is required. The plan reflects your current organizational structure.

## Refresh Cycle

MVB plans refresh every 6 hours to incorporate:

- New users or deprovisioned accounts
- Changes in directory role assignments
- Updated criticality scores from recent activity patterns
- Changes in conditional access policy inventory

Each refresh produces a timestamped plan version. Previous versions are retained for 90 days for audit purposes.

## Accessing MVB Plans

MVB plans are displayed on the Recovery Dashboard under the Recovery Plans section. Each phase shows the estimated resource count, data volume, and projected duration. Plans can be exported as PDF for inclusion in incident response documentation or board reporting.

## Executing a Recovery

During an actual recovery event, the MVB plan serves as the execution guide. Administrators initiate recovery phase by phase, with Shieldio tracking progress and updating the Recovery Confidence Score as each phase completes.
