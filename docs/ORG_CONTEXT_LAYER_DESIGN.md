# Organizational Context Layer — Architecture Design for Agentic Cyber Recovery

**Shieldio | Data Protection for Microsoft 365**
**Date: 2026-03-27 | Status: Design Proposal**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Market Landscape — How Leaders Build Organizational Context](#2-market-landscape)
3. [Microsoft Graph API — Org Context Signal Inventory](#3-microsoft-graph-api-signals)
4. [Per-Workload Intelligent Discovery Signals](#4-per-workload-signals)
5. [Architecture Design — Organizational Context Layer](#5-architecture-design)
6. [Data Model](#6-data-model)
7. [Agentic Cyber Recovery — From Context to Action](#7-agentic-cyber-recovery)
8. [Integration with Existing Shieldio Architecture](#8-integration)
9. [Privacy and Compliance](#9-privacy)
10. [Implementation Phases](#10-phases)

---

## 1. Executive Summary

The Organizational Context Layer is a subsystem that builds and maintains a continuously-updated model of the customer's M365 organizational structure, data criticality, user importance, and collaboration patterns. This context transforms Shieldio from a workload-level backup tool into a **business-aware recovery platform** that can answer: *"Which people and data matter most to keep this organization running?"*

The layer serves two primary functions:

- **Discovery Prioritization** — Focus backup frequency and validation on data that matters most (VIP mailboxes, active SharePoint sites, externally-shared OneDrive files).
- **Recovery Prioritization** — When ransomware hits 50 users, restore the CEO, CFO, and Legal counsel first. Restore the SharePoint Finance Reporting site before an abandoned team site.

This context layer is what turns a recovery runbook into an **agentic recovery system** — one that can reason about blast radius, business impact, and optimal recovery ordering without human instruction at every step.

---

## 2. Market Landscape — How Leaders Build Organizational Context

### 2.1 Rubrik — Intelligent Business Recovery

Rubrik announced **Intelligent Business Recovery for Microsoft 365** at Microsoft Ignite in November 2025. Their approach centers on the concept of a **Minimum Viable Business (MVB)** — the smallest set of users and data needed for the organization to function.

**How it works (three pillars):**

1. **Identify Key Users (Minimum Viable Company)** — Admins pre-define critical groups: C-Suite, Legal, Finance, HR, IT Ops. These become the "MVC" — the people who keep the lights on.

2. **Analyze Critical Workflows** — The system scans M365 protected assets (recent emails, files, SharePoint sites, Teams chats, OneDrive folders) and finds critical data for key users. It analyzes metadata like sensitivity labels and historical context. For example, it does not just restore the CEO's OneDrive — it specifically retrieves files referenced in high-priority email exchanges over the past 30 days.

3. **Automate MVB Recovery** — Recovers the minimum set of data and users first so critical teams can operate immediately, while full recovery continues in the background. The system bypasses M365 API throttling through AI-driven orchestration.

**Key insight:** Rubrik's system includes human-in-the-loop controls — administrators review the AI-generated recovery plan before execution. Users can adjust the plan with natural language ("Add the VP of Comms to this recovery").

**Recovery operates in two phases:** Immediate MVB (critical 7 days of data for priority people) and Full Recovery (everything else, background).

*Sources:*
- [Rubrik: Business-Aware Recovery for M365](https://www.rubrik.com/blog/technology/25/11/business-aware-recovery-for-m365-from-blind-restoration-to-minimum-viable-business-in-minutes)
- [Rubrik: Why Intelligence Is the Missing Link in M365 Recovery](https://www.rubrik.com/blog/company/26/3/speed-is-not-enough-why-intelligence-is-the-missing-link-in-microsft-365-recovery)
- [Rubrik: Intelligent Business Recovery Press Release](https://www.rubrik.com/company/newsroom/press-releases/25/rubrik-introduces-intelligent-business-recovery-for-microsoft-365-and-devops-protection-for-microsoft-environments)

### 2.2 CrowdStrike — Charlotte AI and the Agentic SOC

CrowdStrike has built the most advanced **agentic security operations** platform in the market. Their Fall 2025 release defines the "Falcon agentic security platform" with several relevant components:

- **Charlotte AI Detection Triage** — Triages security detections with over 98% accuracy, eliminating 40+ hours of manual work per week. Operates within customer-defined "bounded autonomy."

- **Charlotte AI AgentWorks** — A no-code platform for building, testing, and deploying security agents. Defenders set goals, define data, and control behavior with natural language.

- **Charlotte Agentic SOAR** (Nov 2025) — Orchestrates AI-powered agents across the security lifecycle. Agents reason and act dynamically together in real time under analyst command.

- **Agentic Security Workforce** — Seven mission-ready agents for key security workflows. The agents reason, decide, and act while automating repetitive tasks.

**Key architectural pattern:** CrowdStrike's agents operate within explicit guardrails — clear explanations, inspectable source data, RBAC, and audit-ready logs. This "bounded autonomy" model keeps analysts in the loop without making them the bottleneck.

**AgentWorks Ecosystem** (RSA 2026, March 25, 2026) — Partners include Anthropic, AWS, NVIDIA, OpenAI, Salesforce. Uses frontier models (Claude, GPT, Nemotron) integrated through Amazon Bedrock/SageMaker.

*Sources:*
- [CrowdStrike: Charlotte AI Agentic Analyst](https://www.crowdstrike.com/en-us/platform/charlotte-ai/)
- [CrowdStrike: Charlotte AI AgentWorks Ecosystem](https://www.crowdstrike.com/en-us/blog/how-charlotte-ai-agentworks-fuels-securitys-agentic-ecosystem/)
- [CrowdStrike: Charlotte Agentic SOAR](https://www.crowdstrike.com/en-us/blog/crowdstrike-leads-new-evolution-of-security-automation-with-charlotte-agentic-soar/)
- [CrowdStrike: Fall 2025 Release — Agentic SOC](https://www.crowdstrike.com/en-us/blog/crowdstrike-fall-2025-release-defines-agentic-soc-secures-ai-era/)

### 2.3 Cohesity — DataHawk and Clean Room Recovery

Cohesity combines three capabilities into **DataHawk**:

- **AI Threat Protection** — Behavioral analytics for ransomware and malicious insider detection. Over 100K threat rules from curated IOC feeds.
- **ML Data Classification** — 230+ classifiers for PII, financial, health, and custom sensitive data patterns.
- **Cyber Vaulting (FortKnox)** — Immutable, air-gapped vaulting with integrated anomaly detection and threat scanning before restore.

**Clean Room concept:** Vaulted data can be mounted into an isolated clean room for forensic analysis and verified recovery before being put back into production. This minimizes risk of secondary attacks.

*Sources:*
- [Cohesity DataHawk](https://www.cohesity.com/platform/datahawk/)
- [Cohesity FortKnox Cyber Vaulting](https://www.cohesity.com/platform/fortknox/)

### 2.4 Microsoft Defender — Security Graph and Context

Microsoft's own security ecosystem builds organizational context through:

- **Microsoft Graph Security API** — Unified schema integrating alerts from Defender for Endpoint, Defender for Cloud, and Identity Protection. Cross-product threat hunting lets security teams create custom queries across all protection products.
- **Cloud Security Graph (Defender CSPM)** — Analyzes assets and connections across the organization to expose lateral movement paths.
- **Incident correlation** — Automatically groups alerts with the same attack techniques or attacker into incidents with organizational context (affected users, devices, scope).

*Sources:*
- [Microsoft Graph Security API Overview](https://learn.microsoft.com/en-us/graph/security-concept-overview)
- [Microsoft Graph Security API Resources](https://learn.microsoft.com/en-us/graph/api/resources/security-api-overview?view=graph-rest-1.0)

### 2.5 Key Patterns Across Leaders

| Pattern | Rubrik | CrowdStrike | Cohesity | Microsoft |
|---------|--------|-------------|----------|-----------|
| Pre-defined critical groups | Yes (MVB) | Yes (bounded autonomy) | No | Partial (risk levels) |
| AI/ML data classification | Yes (metadata + sensitivity labels) | Yes (threat intel) | Yes (230+ classifiers) | Yes (Purview) |
| Human-in-the-loop | Yes (review + NL adjustment) | Yes (analyst command) | Implied | Yes (SOC analyst) |
| Phased recovery | Yes (MVB then full) | N/A | Yes (clean room first) | N/A |
| Organizational graph | Implicit | Yes (threat graph) | Partial | Yes (Cloud Security Graph) |
| Agent-based orchestration | Emerging | Yes (7 agents + SOAR) | No | Emerging (Copilot) |

---

## 3. Microsoft Graph API — Org Context Signal Inventory

These are the specific API endpoints Shieldio can call to build organizational context for each connected tenant. All require appropriate Graph API permissions consented during tenant onboarding.

### 3.1 Organizational Hierarchy

| Signal | Graph API Endpoint | Permission | Refresh Cadence |
|--------|-------------------|------------|-----------------|
| User list + metadata | `GET /users?$select=id,displayName,mail,jobTitle,department,officeLocation,manager` | `User.Read.All` | Daily |
| Manager chain | `GET /users/{id}/manager` | `User.Read.All` | Daily |
| Direct reports | `GET /users/{id}/directReports` | `User.Read.All` | Daily |
| Group membership | `GET /users/{id}/memberOf` | `GroupMember.Read.All` | Daily |
| License assignments | `GET /users/{id}/licenseDetails` | `User.Read.All` | Weekly |

### 3.2 Insights API — Collaboration Signals

| Signal | Graph API Endpoint | Permission | What It Reveals |
|--------|-------------------|------------|-----------------|
| Trending documents | `GET /users/{id}/insights/trending` | `Sites.Read.All` | Which files are gaining attention now |
| Recently used | `GET /users/{id}/insights/used` | `Sites.Read.All` | Active working documents |
| Shared with user | `GET /users/{id}/insights/shared` | `Sites.Read.All` | Collaboration patterns |
| People API | `GET /users/{id}/people` | `People.Read.All` | Virtual teams — who works with whom |

Microsoft's Insights API uses ML to compute these signals from user activity. Documents returned include `resourceVisualization` (title, preview) and `resourceReference` (web URL, type). These signals let Shieldio identify which files a user actually depends on, beyond mere presence in OneDrive.

*Source: [Microsoft Graph — Item Insights Overview](https://learn.microsoft.com/en-us/graph/item-insights-overview)*

### 3.3 Usage Reports

| Signal | Graph API Endpoint | Permission | Refresh |
|--------|-------------------|------------|---------|
| Mailbox usage | `GET /reports/getMailboxUsageDetail(period='D30')` | `Reports.Read.All` | Daily |
| SharePoint site usage | `GET /reports/getSharePointSiteUsageDetail(period='D30')` | `Reports.Read.All` | Daily |
| OneDrive usage | `GET /reports/getOneDriveUsageAccountDetail(period='D30')` | `Reports.Read.All` | Daily |
| Teams team activity | `GET /reports/getTeamsTeamActivityDetail(period='D30')` | `Reports.Read.All` | Daily |
| Teams user activity | `GET /reports/getTeamsUserActivityUserDetail(period='D30')` | `Reports.Read.All` | Daily |

These CSV-format reports give exact metrics: storage used, items count, last activity date, active files, page views, shared files count, active channels, message counts.

### 3.4 Security Signals

| Signal | Graph API Endpoint | Permission | What It Reveals |
|--------|-------------------|------------|-----------------|
| Risky users | `GET /identityProtection/riskyUsers` | `IdentityRiskyUser.Read.All` | Users flagged by Identity Protection |
| Sign-in activity | `GET /auditLogs/signIns` | `AuditLog.Read.All` | Login patterns, locations, risk levels |
| Conditional Access evaluation | `GET /identity/conditionalAccess/policies` | `Policy.Read.All` | Which policies protect which users |
| Security alerts | `GET /security/alerts_v2` | `SecurityAlert.Read.All` | Active security incidents |

### 3.5 Data Classification Signals

| Signal | Graph API Endpoint | Permission | What It Reveals |
|--------|-------------------|------------|-----------------|
| Sensitivity labels (tenant) | `GET /security/informationProtection/sensitivityLabels` | `InformationProtectionPolicy.Read` | Available classification tiers |
| File sensitivity labels | `GET /drives/{id}/items/{id}/extractSensitivityLabels` | `Files.Read.All` | Per-file classification |
| Site sensitivity | Site settings via `/sites/{id}` | `Sites.Read.All` | Site-level classification |

Sensitivity labels are the strongest signal for data criticality — if a customer uses Microsoft Purview, labels like "Highly Confidential", "Confidential", "Internal", "Public" directly indicate business importance.

*Source: [Microsoft Purview Information Protection Labeling](https://learn.microsoft.com/en-us/graph/security-information-protection-overview)*

### 3.6 Entra ID Security Context

| Signal | Graph API Endpoint | Permission |
|--------|-------------------|------------|
| Privileged role assignments | `GET /roleManagement/directory/roleAssignments?$filter=roleDefinition/isPrivileged eq true` | `RoleManagement.Read.Directory` |
| App registrations with high-privilege | `GET /applications` + `GET /servicePrincipals/{id}/appRoleAssignments` | `Application.Read.All` |
| Conditional Access policies | `GET /identity/conditionalAccess/policies` | `Policy.Read.All` |
| PIM eligible assignments | `GET /roleManagement/directory/roleEligibilityScheduleInstances` | `RoleEligibilitySchedule.Read.Directory` |

*Source: [Privileged Roles in Entra ID](https://learn.microsoft.com/en-us/entra/identity/role-based-access-control/privileged-roles-permissions)*

---

## 4. Per-Workload Intelligent Discovery Signals

### 4.1 Exchange — Criticality Signals

| Signal | How to Detect | Criticality Weight |
|--------|--------------|-------------------|
| **VIP mailbox** | User is in executive group, has Global Admin role, or in Legal/Finance department | +40 |
| **High email volume** | `getMailboxUsageDetail` → itemCount, storageUsedInBytes | +10 |
| **External communication** | Mail flow rules, message traces, external recipient patterns | +15 |
| **Sensitivity labels on emails** | `extractSensitivityLabels` on attachments | +25 |
| **Legal hold** | `GET /users/{id}/mailboxSettings` + eDiscovery hold status | +30 |
| **Shared mailboxes** | Mailbox type = shared, many delegates | +10 |
| **Inactive mailbox** | No login in 90+ days (from `signInActivity`) | -20 |

**Composite criticality formula:**
```
exchange_criticality = base_score
  + vip_bonus (40)
  + sensitivity_label_weight (0-25 based on label tier)
  + legal_hold_flag (30)
  + external_comm_ratio * 15
  + log2(email_volume / median_volume) * 10
  - inactive_penalty (20 if no sign-in > 90d)
```

### 4.2 OneDrive — Criticality Signals

| Signal | How to Detect | Criticality Weight |
|--------|--------------|-------------------|
| **Trending documents** | `/insights/trending` — files gaining attention | +20 |
| **Recently used** | `/insights/used` — active working files | +15 |
| **Externally shared** | Sharing permissions include external users | +25 |
| **Large file count** | `getOneDriveUsageAccountDetail` → fileCount, storageUsed | +5 |
| **Sensitivity labels** | `extractSensitivityLabels` on files | +25 |
| **Sync activity** | Active sync client = active user | +10 |

### 4.3 SharePoint — Criticality Signals

| Signal | How to Detect | Criticality Weight |
|--------|--------------|-------------------|
| **High traffic site** | `getSharePointSiteUsageDetail` → visitedPageCount, pageViewCount | +20 |
| **Many unique visitors** | Usage reports → distinct users | +15 |
| **External sharing enabled** | Site sharing settings | +20 |
| **Sensitivity label** | Site-level sensitivity label | +25 |
| **Large document library** | fileCount, storageUsedInBytes | +10 |
| **Root/Hub site** | Site is a hub site or root site collection | +15 |
| **Recently created content** | Active file count in last 30 days | +10 |
| **Abandoned site** | No visits in 90+ days | -15 |

### 4.4 Teams — Criticality Signals

| Signal | How to Detect | Criticality Weight |
|--------|--------------|-------------------|
| **Active channels** | `getTeamsTeamActivityDetail` → activeChannels, channelMessages | +15 |
| **Meeting recordings** | Files in Recordings folder — irreplaceable content | +30 |
| **High message volume** | postMessages + replyMessages | +10 |
| **External participants** | guests + activeExternalUsers in team activity report | +20 |
| **File sharing activity** | Shared files count in channels | +10 |
| **Large team** | Member count > 50 | +5 |

*Source: [Teams Team Activity Detail API](https://learn.microsoft.com/en-us/graph/api/reportroot-getteamsteamactivitydetail?view=graph-rest-1.0)*

### 4.5 Entra ID — Criticality Signals

| Signal | How to Detect | Criticality Weight |
|--------|--------------|-------------------|
| **Global Admin** | Role assignment = Global Administrator | +50 |
| **Privileged roles** | `isPrivileged eq true` on role definitions | +35 |
| **Conditional Access scope** | Policies targeting All Users vs specific groups | +20 |
| **High-privilege app registrations** | Apps with `RoleManagement.ReadWrite.Directory`, `Application.ReadWrite.All` | +30 |
| **Service principal activity** | Active service principals with recent sign-ins | +15 |
| **Break-glass accounts** | Accounts excluded from CA policies (emergency access) | +40 |

---

## 5. Architecture Design — Organizational Context Layer

### 5.1 High-Level Architecture

```
                          ┌──────────────────────────────────────┐
                          │        Microsoft Graph API            │
                          │  (Users, Insights, Reports, Security) │
                          └─────────────────┬────────────────────┘
                                            │
                                     ┌──────▼──────┐
                                     │   Context    │
                                     │  Collector   │
                                     │  (Periodic)  │
                                     └──────┬──────┘
                                            │
                    ┌───────────────────────┼───────────────────────┐
                    │                       │                       │
             ┌──────▼──────┐       ┌───────▼───────┐      ┌───────▼───────┐
             │  Org Graph  │       │  Criticality  │      │   Activity    │
             │   Builder   │       │   Scorer      │      │   Tracker     │
             └──────┬──────┘       └───────┬───────┘      └───────┬───────┘
                    │                       │                       │
                    └───────────────────────┼───────────────────────┘
                                            │
                                   ┌────────▼────────┐
                                   │  Org Context    │
                                   │    Store        │
                                   │  (PostgreSQL)   │
                                   └────────┬────────┘
                                            │
                  ┌─────────────────────────┼─────────────────────────┐
                  │                         │                         │
          ┌───────▼───────┐       ┌────────▼────────┐      ┌────────▼────────┐
          │   Discovery   │       │    Recovery      │      │    Agentic      │
          │  Prioritizer  │       │   Prioritizer    │      │    Recovery     │
          │               │       │                  │      │    Agent        │
          └───────────────┘       └─────────────────┘      └─────────────────┘
```

### 5.2 Storage Strategy — PostgreSQL with Materialized Views

**Decision: PostgreSQL, not a graph database.**

Rationale:
- Shieldio already runs PostgreSQL. Adding Neo4j/Neptune would double operational complexity for a startup.
- The organizational relationships we model (manager chains, group membership, department hierarchy) are bounded-depth trees, not unbounded graph traversals.
- PostgreSQL with `jsonb` columns, recursive CTEs for hierarchy traversal, and materialized views for precomputed scores covers all requirements.
- If graph queries become a bottleneck later (unlikely at our scale), we can add a read-replica with Apache AGE (PostgreSQL graph extension) without changing the primary database.

**Materialized views for performance:**

```sql
-- Precomputed criticality scores, refreshed every 6 hours
CREATE MATERIALIZED VIEW mv_user_criticality AS
SELECT
    po.id AS protected_object_id,
    po.tenant_id,
    po.workload_type,
    po.display_name,
    po.email,
    uc.criticality_score,
    uc.criticality_tier,  -- 'critical', 'high', 'medium', 'low'
    uc.is_vip,
    uc.department,
    uc.job_title,
    uc.manager_chain_json,
    uc.signals_json,      -- which signals contributed to the score
    uc.computed_at
FROM protected_objects po
JOIN user_context uc ON po.id = uc.protected_object_id;

-- Refresh periodically
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_user_criticality;
```

### 5.3 Context Collector — Periodic Sync

The Context Collector runs as a scheduled background task (via the existing worker queue) that syncs organizational signals from Microsoft Graph.

**Sync cadence tiers:**

| Signal Category | Cadence | Rationale |
|----------------|---------|-----------|
| User hierarchy (manager, department, title) | Daily | Changes infrequently |
| Group membership | Daily | Changes infrequently |
| Privileged role assignments | Every 6 hours | Security-critical |
| Usage reports (mailbox, SharePoint, Teams, OneDrive) | Daily | Reports are daily granularity anyway |
| Insights API (trending, used, shared) | Every 12 hours | Moderate change rate |
| Risky users / sign-in activity | Every 4 hours | Security-critical |
| Sensitivity labels | Weekly | Labels change rarely |
| Conditional Access policies | Every 6 hours | Security-critical |

**Graph API throttling mitigation:**
- Batch requests using `$batch` endpoint (up to 20 requests per batch).
- Use delta queries (`/users/delta`) for incremental sync of user changes.
- Respect `Retry-After` headers and implement exponential backoff.
- Stagger syncs across tenants to avoid thundering herd.

### 5.4 Criticality Scorer

The Criticality Scorer computes a 0-100 score for every protected object using the per-workload signals defined in Section 4. It runs after each Context Collector sync.

**Scoring algorithm:**

```python
def compute_criticality(
    protected_object: ProtectedObject,
    user_context: UserContext,
    activity_context: ActivityContext,
) -> CriticalityScore:
    """
    Compute criticality score (0-100) for a protected object.

    Score composition:
    - User importance (40%): VIP status, role, department, privilege level
    - Data sensitivity (30%): Sensitivity labels, external sharing, legal hold
    - Activity level (20%): Usage volume, trending content, collaboration
    - Business dependency (10%): Manager chain depth, direct reports count
    """

    # User importance (0-100, weighted 40%)
    user_score = 0
    if user_context.is_global_admin:
        user_score = 100
    elif user_context.has_privileged_role:
        user_score = 80
    elif user_context.is_vip:  # Executive group member
        user_score = 90
    elif user_context.department in ('Legal', 'Finance', 'HR', 'IT'):
        user_score = 60
    else:
        user_score = 30

    # Data sensitivity (0-100, weighted 30%)
    sensitivity_score = 0
    if user_context.highest_sensitivity_label == 'Highly Confidential':
        sensitivity_score = 100
    elif user_context.highest_sensitivity_label == 'Confidential':
        sensitivity_score = 70
    elif user_context.has_legal_hold:
        sensitivity_score = 90
    elif user_context.external_sharing_active:
        sensitivity_score = 50
    else:
        sensitivity_score = 20

    # Activity level (0-100, weighted 20%)
    # Normalize against tenant median
    activity_score = min(100, (activity_context.relative_activity * 50) + 25)

    # Business dependency (0-100, weighted 10%)
    dep_score = min(100, user_context.direct_reports_count * 10 + 20)

    total = (
        user_score * 0.40 +
        sensitivity_score * 0.30 +
        activity_score * 0.20 +
        dep_score * 0.10
    )

    tier = (
        'critical' if total >= 80 else
        'high' if total >= 60 else
        'medium' if total >= 40 else
        'low'
    )

    return CriticalityScore(
        score=round(total),
        tier=tier,
        signals={...},  # Which signals contributed
    )
```

### 5.5 Context Freshness and Cache Invalidation

| Layer | TTL | Invalidation Strategy |
|-------|-----|----------------------|
| In-memory cache (per-request) | 5 minutes | Time-based expiry |
| Materialized views | 6 hours | Scheduled `REFRESH CONCURRENTLY` |
| Raw context tables | Sync cadence per signal type | Upsert on each collector run |
| Change notifications (Graph webhooks) | Real-time | Webhook triggers immediate re-sync for critical changes |

**Graph Change Notifications** for real-time updates on:
- User property changes (department, manager, job title)
- Group membership changes
- Security alerts

---

## 6. Data Model

### 6.1 New Tables

```sql
-- ══════════════════════════════════════════════════════════
-- Organizational Context Tables
-- ══════════════════════════════════════════════════════════

-- User-level organizational context
CREATE TABLE user_context (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    protected_object_id INTEGER REFERENCES protected_objects(id),
    ms_user_id VARCHAR(255) NOT NULL,

    -- Hierarchy
    display_name VARCHAR(500),
    email VARCHAR(255),
    job_title VARCHAR(255),
    department VARCHAR(255),
    office_location VARCHAR(255),
    manager_ms_id VARCHAR(255),
    manager_chain_json TEXT,           -- JSON array of manager IDs up to CEO
    direct_reports_count INTEGER DEFAULT 0,

    -- Criticality
    criticality_score INTEGER DEFAULT 50,  -- 0-100
    criticality_tier VARCHAR(20) DEFAULT 'medium',  -- critical/high/medium/low
    is_vip BOOLEAN DEFAULT FALSE,

    -- Security context
    has_privileged_role BOOLEAN DEFAULT FALSE,
    privileged_roles_json TEXT,        -- JSON array of role names
    is_global_admin BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(20),            -- none/low/medium/high from Identity Protection
    last_sign_in_at TIMESTAMP,

    -- Data sensitivity
    highest_sensitivity_label VARCHAR(100),
    has_legal_hold BOOLEAN DEFAULT FALSE,
    external_sharing_active BOOLEAN DEFAULT FALSE,

    -- License
    license_skus_json TEXT,            -- JSON array of assigned licenses

    -- Activity (from usage reports)
    mailbox_item_count INTEGER,
    mailbox_size_bytes BIGINT,
    onedrive_file_count INTEGER,
    onedrive_size_bytes BIGINT,
    last_activity_at TIMESTAMP,

    -- Signals metadata
    signals_json TEXT,                 -- JSON: which signals contributed to score

    -- Timestamps
    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, ms_user_id)
);

CREATE INDEX idx_user_context_tenant_score
    ON user_context(tenant_id, criticality_score DESC);
CREATE INDEX idx_user_context_tier
    ON user_context(tenant_id, criticality_tier);
CREATE INDEX idx_user_context_department
    ON user_context(tenant_id, department);

-- Site-level organizational context (SharePoint + Teams)
CREATE TABLE site_context (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    protected_object_id INTEGER REFERENCES protected_objects(id),
    ms_site_id VARCHAR(255) NOT NULL,

    -- Site metadata
    site_url VARCHAR(1000),
    site_name VARCHAR(500),
    site_type VARCHAR(50),             -- team_site, communication_site, hub_site

    -- Activity
    page_view_count INTEGER DEFAULT 0,
    visited_page_count INTEGER DEFAULT 0,
    unique_visitors INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    active_file_count INTEGER DEFAULT 0,
    storage_used_bytes BIGINT DEFAULT 0,
    last_activity_at TIMESTAMP,

    -- Sensitivity
    sensitivity_label VARCHAR(100),
    external_sharing_enabled BOOLEAN DEFAULT FALSE,

    -- Criticality
    criticality_score INTEGER DEFAULT 50,
    criticality_tier VARCHAR(20) DEFAULT 'medium',
    signals_json TEXT,

    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, ms_site_id)
);

-- Team-level context
CREATE TABLE team_context (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    protected_object_id INTEGER REFERENCES protected_objects(id),
    ms_team_id VARCHAR(255) NOT NULL,

    team_name VARCHAR(500),
    active_channels INTEGER DEFAULT 0,
    active_users INTEGER DEFAULT 0,
    guests INTEGER DEFAULT 0,
    active_external_users INTEGER DEFAULT 0,
    post_messages INTEGER DEFAULT 0,
    reply_messages INTEGER DEFAULT 0,
    channel_messages INTEGER DEFAULT 0,
    urgent_messages INTEGER DEFAULT 0,
    meetings_organized INTEGER DEFAULT 0,
    has_meeting_recordings BOOLEAN DEFAULT FALSE,

    criticality_score INTEGER DEFAULT 50,
    criticality_tier VARCHAR(20) DEFAULT 'medium',
    signals_json TEXT,

    last_activity_at TIMESTAMP,
    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
    computed_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, ms_team_id)
);

-- VIP group definitions (admin-defined)
CREATE TABLE vip_groups (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,        -- e.g., 'Executive Leadership', 'Legal Team'
    description TEXT,
    priority INTEGER DEFAULT 1,        -- 1 = highest priority for recovery
    source VARCHAR(50) DEFAULT 'manual',  -- manual, entra_group, auto_detected
    ms_group_id VARCHAR(255),          -- If linked to an Entra ID group
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Members of VIP groups
CREATE TABLE vip_group_members (
    id SERIAL PRIMARY KEY,
    vip_group_id INTEGER NOT NULL REFERENCES vip_groups(id),
    user_context_id INTEGER NOT NULL REFERENCES user_context(id),
    added_at TIMESTAMP DEFAULT NOW(),
    added_by VARCHAR(255),             -- admin who added, or 'auto' for auto-detected
    UNIQUE(vip_group_id, user_context_id)
);

-- Entra ID security context
CREATE TABLE entra_context (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),

    -- Conditional Access
    ca_policies_count INTEGER DEFAULT 0,
    ca_policies_json TEXT,             -- Summary of policies and their scope

    -- Privileged roles
    global_admin_count INTEGER DEFAULT 0,
    privileged_role_count INTEGER DEFAULT 0,
    privileged_users_json TEXT,        -- List of privileged user IDs

    -- App registrations
    high_priv_apps_count INTEGER DEFAULT 0,
    high_priv_apps_json TEXT,

    -- Break-glass accounts
    break_glass_accounts_json TEXT,

    criticality_score INTEGER DEFAULT 80,  -- Entra is always high criticality
    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id)
);

-- Recovery priority plan (generated by agentic system)
CREATE TABLE recovery_plans (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    plan_type VARCHAR(50) NOT NULL,    -- mvb, ransomware, selective, full
    status VARCHAR(50) DEFAULT 'draft', -- draft, approved, executing, completed

    -- Plan content
    affected_users_count INTEGER DEFAULT 0,
    affected_objects_count INTEGER DEFAULT 0,
    blast_radius_json TEXT,            -- Departments/sites/teams affected

    -- Priority ordering (JSON array of recovery phases)
    phases_json TEXT,
    -- Example phases_json:
    -- [
    --   {"phase": 1, "name": "MVB - Executive", "objects": [...], "estimated_minutes": 15},
    --   {"phase": 2, "name": "MVB - Legal & Finance", "objects": [...], "estimated_minutes": 30},
    --   {"phase": 3, "name": "Critical SharePoint Sites", "objects": [...], "estimated_minutes": 45},
    --   {"phase": 4, "name": "Full Recovery - Remaining", "objects": [...], "estimated_minutes": 240}
    -- ]

    -- Agent reasoning
    agent_reasoning_json TEXT,         -- Why the agent made these decisions

    -- Approval
    approved_by INTEGER REFERENCES users(id),
    approved_at TIMESTAMP,

    -- Execution
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    restore_jobs_json TEXT,            -- IDs of spawned restore jobs

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 6.2 Additions to Existing Models

The existing `ProtectedObject` model gets a lightweight link:

```python
# Add to ProtectedObject model
criticality_score = Column(Integer, default=50)
criticality_tier = Column(String(20), default='medium')
```

This denormalized field avoids joins for the most common query pattern (list objects sorted by criticality).

---

## 7. Agentic Cyber Recovery — From Context to Action

### 7.1 What "Agentic" Means in Cyber Recovery

"Agentic" recovery means the system can **reason about the situation, generate a plan, and execute it** — with human approval at critical decision points. This is distinct from:

- **Rule-based recovery:** IF ransomware THEN restore all from yesterday. No reasoning, no prioritization.
- **Runbook-based recovery:** Human follows a static checklist. The existing Shieldio runbooks in `recovery.py` are this model.
- **Agentic recovery:** The system analyzes the blast radius, cross-references org context to identify affected VIPs, determines optimal recovery ordering, presents a plan to the admin, and executes upon approval.

### 7.2 Agent Architecture — Recovery Agent

```
┌─────────────────────────────────────────────────────────┐
│                    Recovery Agent                         │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│  │ Situation │  │  Blast   │  │ Recovery │  │Execution│ │
│  │ Assessor │──▶ Radius  │──▶│  Plan   │──▶│ Engine  │ │
│  │          │  │ Analyzer │  │Generator │  │         │ │
│  └──────────┘  └──────────┘  └──────────┘  └─────────┘ │
│       │              │              │             │       │
│       ▼              ▼              ▼             ▼       │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Org Context Store                     │   │
│  │  (user_context, site_context, team_context,       │   │
│  │   vip_groups, entra_context)                      │   │
│  └──────────────────────────────────────────────────┘   │
│                          │                               │
│                 ┌────────▼────────┐                      │
│                 │  Human-in-the-  │                      │
│                 │  Loop Gateway   │                      │
│                 └─────────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### 7.3 Scenario 1 — Ransomware Recovery

**Trigger:** Admin clicks "Ransomware Recovery" or agent detects anomaly affecting 50+ users.

**Step 1: Situation Assessment**
```
Input: "Ransomware detected affecting 50 users"
Agent queries:
  - SELECT * FROM user_context WHERE ms_user_id IN (...affected_ids...)
  - What departments are hit?
  - Are any VIP group members affected?
  - What's the earliest anomaly timestamp?
```

**Step 2: Blast Radius Analysis**
```
Agent determines:
  - 50 users affected across 4 departments
  - 3 VIP members hit: CFO, Head of Legal, VP Engineering
  - 12 SharePoint sites with activity from affected users
  - 8 Teams with affected members
  - Blast radius: Finance (18 users), Engineering (15), Legal (10), Marketing (7)
  - Earliest anomaly: 2026-03-26 14:30 UTC
```

**Step 3: Recovery Plan Generation**
```json
{
  "plan_type": "ransomware",
  "incident_start": "2026-03-26T14:30:00Z",
  "restore_to": "2026-03-26T14:00:00Z",
  "phases": [
    {
      "phase": 1,
      "name": "Entra ID Security Controls",
      "priority": "immediate",
      "objects": ["Conditional Access Policies", "Security Groups", "MFA Settings"],
      "reason": "Restore identity controls first to prevent re-compromise",
      "estimated_minutes": 5
    },
    {
      "phase": 2,
      "name": "Executive & Legal (MVB)",
      "priority": "critical",
      "objects": [
        {"type": "exchange", "user": "CFO", "criticality": 95},
        {"type": "exchange", "user": "Head of Legal", "criticality": 92},
        {"type": "onedrive", "user": "CFO", "criticality": 95},
        {"type": "onedrive", "user": "Head of Legal", "criticality": 92}
      ],
      "reason": "C-Suite and Legal must be operational for incident response decisions and regulatory obligations",
      "estimated_minutes": 15
    },
    {
      "phase": 3,
      "name": "Finance Department",
      "priority": "high",
      "objects": ["18 Exchange mailboxes", "18 OneDrive accounts", "Finance Reporting SharePoint site"],
      "reason": "Finance handles payroll, vendor payments, and financial reporting — business continuity depends on it",
      "estimated_minutes": 45
    },
    {
      "phase": 4,
      "name": "Critical SharePoint Sites",
      "priority": "high",
      "objects": ["Top 5 sites by criticality score from site_context"],
      "reason": "High-traffic sites with external sharing or confidential labels",
      "estimated_minutes": 30
    },
    {
      "phase": 5,
      "name": "Remaining Users — Full Recovery",
      "priority": "normal",
      "objects": ["Remaining 29 users across Engineering, Marketing"],
      "reason": "Complete recovery of all affected users",
      "estimated_minutes": 180
    }
  ],
  "total_estimated_minutes": 275,
  "agent_reasoning": "Prioritized Entra ID first (identity controls), then VIPs (CFO, Legal head), then Finance department (business-critical), then high-traffic SharePoint sites. Engineering and Marketing deferred to Phase 5 as they have lower immediate business impact."
}
```

**Step 4: Human Approval**
```
The plan is presented to the admin in the Shieldio UI.
Admin can:
  - Approve as-is → Execute
  - Modify (add/remove users, change phase ordering)
  - Use natural language: "Move VP Engineering to Phase 2"
  - Reject and start over
```

**Step 5: Execution**
```
For each phase:
  1. Find closest clean snapshot before restore_to timestamp
  2. Run malware scan on selected snapshot
  3. Dispatch restore jobs (using existing RestoreJob model)
  4. Track progress, report per-phase completion
  5. Verify item counts match pre-incident baseline
```

### 7.4 Scenario 2 — Self-Service Intelligent Restore

**Trigger:** End user says "I need my deleted contract with Acme Corp"

**Step 1: Understand User Context**
```
Agent queries user_context:
  - User: Jane Smith, Legal Department, criticality_tier: high
  - Recent activity: Active OneDrive user, 40 files used in last 30 days
  - Department context: Legal team works with contracts
```

**Step 2: Intelligent Search**
```
Agent searches backup data with context enrichment:
  - Search term: "contract Acme Corp"
  - Scope: Jane's Exchange + OneDrive (most likely locations)
  - Time range: Last 90 days of snapshots
  - Boost: Files with sensitivity label "Confidential"
  - Boost: Files that appeared in /insights/used or /insights/trending
```

**Step 3: Ranked Results**
```
1. "Acme Corp - Master Services Agreement v3.docx" (OneDrive, deleted 3 days ago)
   Confidence: 95% — matches search term, recently used, sensitivity: Confidential
2. "RE: Acme Corp Contract Review" (Exchange, attachment)
   Confidence: 70% — email with contract in subject, has PDF attachment
3. "Acme Corp NDA 2025.pdf" (OneDrive, deleted 3 days ago)
   Confidence: 50% — matches "Acme Corp" but is NDA not contract
```

**Step 4: One-Click Restore**
```
User selects item 1 → Restore to original OneDrive location
Agent handles: find snapshot, decrypt, restore, verify
```

### 7.5 Human-in-the-Loop Patterns

Every agentic action in Shieldio follows the **bounded autonomy** model:

| Action Type | Autonomy Level | Approval Required |
|-------------|---------------|-------------------|
| Build org context (read signals) | Full autonomy | No |
| Compute criticality scores | Full autonomy | No |
| Generate recovery plan | Full autonomy | No |
| Execute MVB recovery (< 10 objects) | Requires approval | Admin click |
| Execute mass recovery (10+ objects) | Requires approval | Admin click + confirmation |
| Modify Entra ID configuration | Requires approval | Admin click + MFA |
| Self-service restore (single item) | Requires approval | User click |
| Change VIP group membership | Requires approval | Admin click |

---

## 8. Integration with Existing Shieldio Architecture

### 8.1 Where Org Context Plugs In

```
Existing Shieldio                    New Org Context Layer
────────────────                     ─────────────────────
Discovery (tenant sync)    ──────▶   Context Collector runs after discovery
SLA Policies               ──────▶   Criticality score influences SLA assignment
Backup Scheduler           ──────▶   Higher criticality = more frequent validation
Mass Recovery              ──────▶   Recovery Prioritizer orders restore jobs
Recovery Confidence Score  ──────▶   Weighted by criticality (VIP coverage matters more)
Self-Service Restore       ──────▶   Context-enriched search results
Anomaly Detection          ──────▶   VIP anomalies get higher alert severity
Dashboard                  ──────▶   Org context visualization (risk map, VIP status)
```

### 8.2 Modified Discovery Flow

Current flow:
```
Tenant Onboarding → Graph Discovery → Create ProtectedObjects → Done
```

New flow:
```
Tenant Onboarding → Graph Discovery → Create ProtectedObjects
                                          │
                                    Context Collector
                                          │
                              ┌───────────┼───────────┐
                              │           │           │
                         user_context  site_context  team_context
                              │           │           │
                              └───────────┼───────────┘
                                          │
                                  Criticality Scorer
                                          │
                              Update protected_objects.criticality_score
                                          │
                              Auto-assign VIP groups (if detected)
```

### 8.3 Modified Mass Recovery Flow

Current `mass_restore()` in `recovery.py` treats all objects equally — it simply iterates protected objects and dispatches restore jobs. The new flow:

```python
# Pseudocode for context-aware mass recovery
async def intelligent_mass_restore(req: MassRecoveryRequest):
    # 1. Get all affected objects with criticality context
    objects = await get_protected_objects_with_context(
        tenant_id=req.tenant_id,
        workload_types=req.workload_types,
    )

    # 2. Generate phased recovery plan
    plan = await recovery_agent.generate_plan(
        objects=objects,
        restore_point=req.restore_point,
        incident_type=req.incident_type,  # NEW: ransomware, accidental, etc.
    )

    # 3. Return plan for human approval (if not dry_run)
    if req.dry_run or not req.auto_approve:
        return {"status": "plan_generated", "plan": plan}

    # 4. Execute phased recovery
    for phase in plan.phases:
        phase_jobs = []
        for obj in phase.objects:
            job = await create_restore_job(obj, req.restore_point)
            phase_jobs.append(job)

        # Wait for phase completion before starting next
        await wait_for_phase(phase_jobs)

        # Verify phase recovery
        await verify_phase_recovery(phase_jobs)

    return {"status": "completed", "plan": plan}
```

### 8.4 New API Endpoints

```
POST /api/org-context/sync              — Trigger manual context sync for a tenant
GET  /api/org-context/summary           — Org context dashboard summary
GET  /api/org-context/users             — List users with criticality scores
GET  /api/org-context/sites             — List sites with criticality scores
GET  /api/org-context/vip-groups        — List VIP groups and members
POST /api/org-context/vip-groups        — Create/update VIP group
GET  /api/org-context/blast-radius      — Compute blast radius for a set of affected objects
POST /api/recovery/intelligent-restore  — Generate context-aware recovery plan
POST /api/recovery/execute-plan         — Execute an approved recovery plan
GET  /api/recovery/plans                — List recovery plans (draft/approved/completed)
```

---

## 9. Privacy and Compliance Considerations

### 9.1 What We Store vs. What We Derive

| Data | Store? | Rationale |
|------|--------|-----------|
| User display name, email, department, title | Yes | Needed for VIP identification and plan generation |
| Manager chain | Yes | Needed for org hierarchy and blast radius |
| Criticality score (computed) | Yes | Core feature — must be fast to query |
| Email content / file content | No | We already store this in backups; context layer is metadata only |
| Specific collaboration partners | No | Derive on-demand from Insights API; don't cache |
| Sign-in IP addresses | No | Only store last_sign_in_at timestamp |
| Sensitivity label names | Yes | Critical for data classification scoring |
| Exact message counts | Yes (aggregated) | From usage reports, not individual messages |

### 9.2 Data Retention

- Org context data follows the same tenant lifecycle as backup data.
- When a tenant is offboarded, all `user_context`, `site_context`, `team_context`, and related rows are deleted.
- Historical criticality scores are not retained — only the current computed score.

### 9.3 Permissions Scope

Required Microsoft Graph permissions (incremental over existing):

| Permission | Type | Purpose |
|-----------|------|---------|
| `User.Read.All` | Application | User hierarchy, managers, departments |
| `Reports.Read.All` | Application | Usage reports for all workloads |
| `Sites.Read.All` | Application (already have) | Insights API, sensitivity labels |
| `People.Read.All` | Delegated | Collaboration graph (optional) |
| `IdentityRiskyUser.Read.All` | Application | Risk-based prioritization |
| `RoleManagement.Read.Directory` | Application | Privileged role detection |
| `Policy.Read.All` | Application | Conditional Access policy scope |
| `InformationProtectionPolicy.Read` | Application | Sensitivity label definitions |
| `SecurityAlert.Read.All` | Application | Active incident correlation |

### 9.4 Admin Consent and Transparency

- During tenant onboarding, Shieldio requests these additional permissions with clear explanations of what each is used for.
- Admins can opt out of specific signal categories (e.g., "Don't collect usage reports").
- An admin dashboard shows exactly what org context Shieldio has collected for their tenant.
- All context sync operations are logged in the existing audit trail.

---

## 10. Implementation Phases

### Phase 1: Foundation (4-6 weeks)
- [ ] Database migrations: `user_context`, `site_context`, `team_context`, `vip_groups` tables
- [ ] Context Collector service: User hierarchy sync, usage reports sync
- [ ] Basic Criticality Scorer: Score based on department, role, VIP group membership
- [ ] Add `criticality_score` and `criticality_tier` to `ProtectedObject` model
- [ ] VIP Group CRUD API + UI
- [ ] Admin dashboard: "Org Context" page showing users by criticality tier

### Phase 2: Signal Enrichment (3-4 weeks)
- [ ] Insights API integration (trending, used, shared)
- [ ] Security signals: risky users, privileged roles, Conditional Access
- [ ] Sensitivity label detection
- [ ] Teams and SharePoint activity integration
- [ ] Full Criticality Scorer with all per-workload signals
- [ ] Materialized view for precomputed scores

### Phase 3: Context-Aware Recovery (4-5 weeks)
- [ ] Recovery Plan Generator: Takes affected objects + org context, produces phased plan
- [ ] Recovery Plan UI: Visual display of phases with drag-to-reorder
- [ ] Phased execution engine: Execute plan phase-by-phase with verification
- [ ] Modify existing `mass_restore()` to use criticality ordering
- [ ] Blast radius analyzer: Given N affected users, show departments/sites/teams impacted
- [ ] Recovery Confidence Score weighted by criticality coverage

### Phase 4: Agentic Layer (6-8 weeks)
- [ ] LLM integration (Claude API) for natural language recovery plan adjustment
- [ ] Self-service intelligent search with context-boosted results
- [ ] Agent-generated recovery plans with reasoning explanations
- [ ] Natural language interface: "Restore Finance department to yesterday"
- [ ] Anomaly-triggered automatic plan generation (admin approval still required)
- [ ] Recovery plan templates that learn from past recoveries

### Phase 5: Advanced Signals (Ongoing)
- [ ] Graph webhooks for real-time context updates
- [ ] Collaboration graph analysis (who works with whom)
- [ ] Predictive criticality: ML model trained on actual recovery patterns
- [ ] Cross-tenant context for MSP/multi-tenant deployments
- [ ] Integration with CrowdStrike/Defender alerts as recovery triggers

---

## Appendix A: Graph API Permission Mapping

```
Current Shieldio Permissions:
  - Mail.ReadWrite            (Exchange backup/restore)
  - Files.ReadWrite.All       (OneDrive/SharePoint backup/restore)
  - Sites.ReadWrite.All       (SharePoint site operations)
  - Group.Read.All            (Teams discovery)
  - ChannelMessage.Read.All   (Teams message backup)
  - User.Read.All             (User discovery)
  - Directory.Read.All        (Entra ID backup)

New Permissions for Org Context Layer:
  + Reports.Read.All          (Usage analytics — mailbox, SharePoint, Teams, OneDrive)
  + IdentityRiskyUser.Read.All (Identity Protection risk signals)
  + RoleManagement.Read.Directory (Privileged role assignments)
  + Policy.Read.All           (Conditional Access policy scope)
  + InformationProtectionPolicy.Read (Sensitivity label definitions)
  + SecurityAlert.Read.All    (Active security incident correlation)
```

## Appendix B: Competitive Positioning

| Capability | Rubrik | Cohesity | Shieldio (Proposed) |
|-----------|--------|----------|-------------------|
| MVB / Priority Users | Admin-defined groups | No | Admin-defined + auto-detected from Graph |
| Data Criticality Scoring | Sensitivity labels + email analysis | ML classifiers (230+) | Multi-signal scoring (Graph + usage + security) |
| Recovery Plan Generation | AI-generated with NL adjustment | Manual | Agent-generated with NL adjustment |
| Blast Radius Analysis | Not public | Not public | Department/site/team impact mapping |
| Phased Recovery | Yes (MVB then full) | Yes (clean room first) | Yes (multi-phase with per-phase verification) |
| Self-Service Context | Not public | No | User context enriches search results |
| Real-time Context | Not public | No | Graph webhooks + periodic sync |
| Agentic Orchestration | Emerging | No | LLM-powered agent with bounded autonomy |

**Shieldio differentiator:** Deep Graph API integration gives us organizational context signals that are unique to the M365 ecosystem. Rubrik and Cohesity are multi-cloud platforms that must abstract across providers. Shieldio's M365-native focus means we can exploit every Graph API endpoint for richer context than any cross-platform competitor.
