# Research Analysis: Databricks Lakewatch + Anthropic Cyber Capabilities
## Impact on KavachIQ Organizational Context Layer Design

**Date: 2026-03-27 | Status: Research Analysis**

---

## 1. What Changed Since Our Original Design

Our `ORG_CONTEXT_LAYER_DESIGN.md` was written based on the competitive landscape as of early 2026 (Rubrik MVB, CrowdStrike Charlotte AI, Cohesity DataHawk). Two major developments in the last week fundamentally shift what's possible:

### Databricks Lakewatch (Announced March 24, 2026)
- Open, agentic SIEM built on the Data Intelligence Platform
- Bronze/Silver/Gold lakehouse architecture for security telemetry
- **OCSF** (Open Cybersecurity Schema Framework) as the normalization standard
- Agent Bricks for building custom security agents
- Unity Catalog for governance, data classification, and organizational context
- Partners: Anthropic Claude, Palo Alto, Okta, Zscaler, Wiz
- Early customers: Adobe, Dropbox, National Australia Bank (30TB/day)
- **Key insight**: Security data enriched with business context (HR roles, asset criticality, geography) in the Silver layer

### Anthropic Cyber Capabilities (RSA 2026, March 25-27, 2026)
- **Claude Code Security**: Reasoning-based vulnerability discovery (500+ zero-days in production OSS)
- **Accenture Cyber.AI**: Claude as reasoning engine for cyber resiliency agents
- **CrowdStrike AgentWorks**: Claude as a frontier model alongside GPT/Nemotron for custom security agents
- **Claude Mythos** (leaked, unreleased): Described as "far ahead of any other AI model in cyber capabilities"
- **Key insight**: Multi-stage verification pattern (find -> verify -> rate confidence -> present for human approval)

---

## 2. What This Means for KavachIQ

### The Opportunity
Lakewatch validates our thesis but from the SIEM side: **security is a data problem that requires organizational context**. Lakewatch enriches security telemetry with business context for detection. KavachIQ enriches backup data with business context for recovery.

**Nobody is doing both.** The market is splitting into:
- **Detection** (Lakewatch, CrowdStrike, Defender) — "What happened?"
- **Recovery** (Rubrik, KavachIQ) — "How do we get back?"

The gap: detection systems don't know your backup state, and backup systems don't know your threat state. **KavachIQ can bridge this.**

### The Differentiators We Can Build

| Capability | Rubrik | Lakewatch | KavachIQ (Proposed) |
|-----------|--------|-----------|-------------------|
| Org context source | Admin-defined VIP groups | SIEM telemetry + HR data | Auto-detected from M365 Graph + SIEM signals |
| Data classification | Sensitivity labels only | Unity Catalog AI classification | Sensitivity labels + content-aware scoring |
| Recovery intelligence | MVB (pre-defined) | N/A (detection only) | MVB + dynamic criticality + threat-informed |
| Threat-informed recovery | No | N/A | Yes — integrate SIEM signals into restore decisions |
| Agentic reasoning | Emerging | Agent Bricks | Claude-powered recovery agent with bounded autonomy |
| Open schema | Proprietary | OCSF | OCSF-compatible (for SIEM integration) |

---

## 3. Design Improvements — What We Should Change

### 3.1 Adopt OCSF for Threat Signal Ingestion

**Current design**: Our Context Collector syncs org signals from Microsoft Graph only.

**Improved design**: Add an OCSF-compatible threat signal ingestion layer. This lets KavachIQ consume security events from Lakewatch, CrowdStrike, Defender, or any OCSF-producing SIEM — and use those signals to inform recovery decisions.

**Why this matters**: When Lakewatch or CrowdStrike detects ransomware, KavachIQ should automatically receive that signal, correlate it with backup state, and generate a recovery plan — without the admin manually switching between tools.

```
SIEM (Lakewatch/CrowdStrike/Defender)
    │
    │  OCSF security events
    ▼
┌──────────────────┐
│  Threat Signal   │  ← NEW: OCSF ingestion endpoint
│  Receiver        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Org Context     │  ← EXISTING: enriched with threat state
│  Store           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Recovery Agent  │  ← EXISTING: now threat-informed
│  (Claude)        │
└──────────────────┘
```

**New API endpoint**:
```
POST /api/threat-signals/ingest   — Receive OCSF-formatted security events
POST /api/threat-signals/webhook  — Webhook for real-time SIEM alerts
```

### 3.2 Threat-Informed Recovery (New Capability)

**Current design**: Recovery plans are based on criticality scores only. "Restore the CEO first because they're important."

**Improved design**: Recovery plans factor in the **threat vector**. "Restore the CEO first because they're important AND their account was the entry point for the attack, so we need to verify their Entra ID state before restoring data."

**Threat-informed recovery logic**:
```
For each affected object:
  criticality_score (from org context)         — WHO matters
  + threat_exposure_score (from SIEM signals)  — WHO was targeted
  + data_sensitivity_score (from labels)       — WHAT matters
  + backup_freshness (from snapshot state)     — WHAT's available
  = recovery_priority
```

This is what Rubrik cannot do — they have no SIEM integration. And what Lakewatch cannot do — they have no backup state.

### 3.3 Claude-Powered Recovery Agent with Multi-Stage Verification

**Current design (Phase 4)**: "LLM integration for natural language recovery plan adjustment."

**Improved design**: Adopt Anthropic's multi-stage verification pattern from Claude Code Security:

```
Stage 1: ASSESS
  Claude analyzes blast radius using org context + SIEM signals
  "50 users affected. 3 VIPs. Finance department hit hardest.
   Attack vector: compromised OAuth app with Mail.ReadWrite permissions."

Stage 2: PLAN
  Claude generates phased recovery plan with reasoning
  "Phase 1: Revoke OAuth app + restore Entra ID CA policies (5 min)
   Phase 2: Restore CFO + Legal Head mailboxes (15 min)
   Phase 3: Restore Finance department (45 min)
   Reasoning: OAuth app was the entry vector, must be revoked before
   any data restore to prevent re-compromise."

Stage 3: VERIFY
  Claude re-analyzes its own plan for logical errors
  "Verification: Plan correctly prioritizes identity before data.
   Risk check: No restored snapshots are from after compromise time.
   Confidence: 92%"

Stage 4: PRESENT
  Admin reviews plan with confidence scores and reasoning
  Can modify via natural language: "Add VP Engineering to Phase 2"

Stage 5: EXECUTE + MONITOR
  Phased execution with per-phase verification
  Agent monitors for anomalies during recovery
```

This is directly inspired by Claude Code Security's "find, verify, rate confidence, present for human approval" workflow — but applied to cyber recovery instead of vulnerability discovery.

### 3.4 Bronze/Silver/Gold for Backup Intelligence

**Inspired by Lakewatch's lakehouse architecture**, apply the medallion pattern to KavachIQ's backup metadata:

```
Bronze (Raw):
  - Raw Graph API responses (users, groups, policies)
  - Raw backup metadata (snapshots, items, sizes)
  - Raw SIEM signals (OCSF events)

Silver (Enriched):
  - Users enriched with hierarchy, department, criticality
  - Backup items enriched with sensitivity labels, activity scores
  - Threat events correlated with affected backup objects
  - Cross-referenced: "This backup snapshot was taken AFTER the compromise"

Gold (Actionable):
  - Pre-computed recovery plans (updated every 6 hours)
  - Recovery readiness score weighted by criticality + threat state
  - "What-if" recovery simulations cached for instant response
  - MVB (Minimum Viable Business) set auto-maintained
```

The Gold layer is the killer feature: **pre-computed recovery plans ready to execute instantly** when an incident happens. No human needs to think about ordering or priority — the plan exists before the attack.

### 3.5 Agent-to-Agent Trust (Inspired by Antimatter Acquisition)

Databricks acquired Antimatter for agent-to-agent trust — solving "how do AI agents authenticate to each other securely?" This is relevant for KavachIQ's agentic recovery:

- The Recovery Agent needs to authenticate to the Execution Engine
- The Execution Engine needs to authenticate to Microsoft Graph
- Audit trail must prove which agent took which action and why

**Design principle**: Every agentic action in the recovery pipeline must be:
1. **Attributable** — which agent, which reasoning, which input data
2. **Auditable** — full decision chain logged for compliance
3. **Bounded** — human approval gates at every destructive action
4. **Reversible** — any agent action can be undone within the approval window

---

## 4. Revised Architecture

```
                    ┌────────────────────────────────────┐
                    │        External Signals              │
                    │  ┌──────────┐  ┌──────────────────┐ │
                    │  │  M365    │  │  SIEM (OCSF)     │ │
                    │  │  Graph   │  │  Lakewatch /      │ │
                    │  │  API     │  │  CrowdStrike /    │ │
                    │  │          │  │  Defender          │ │
                    │  └────┬─────┘  └────────┬─────────┘ │
                    └───────┼─────────────────┼───────────┘
                            │                 │
                    ┌───────▼─────────────────▼───────────┐
                    │         BRONZE LAYER                  │
                    │  Raw org signals + Raw threat events  │
                    └───────────────────┬─────────────────┘
                                        │
                    ┌───────────────────▼─────────────────┐
                    │         SILVER LAYER                  │
                    │  Enriched context: users, sites,     │
                    │  teams with criticality + threat     │
                    │  exposure + sensitivity scores       │
                    └───────────────────┬─────────────────┘
                                        │
                    ┌───────────────────▼─────────────────┐
                    │          GOLD LAYER                   │
                    │  Pre-computed recovery plans          │
                    │  MVB sets, what-if simulations        │
                    │  Recovery readiness (weighted)        │
                    └───────────────────┬─────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
      ┌───────▼───────┐      ┌─────────▼─────────┐     ┌────────▼────────┐
      │   Recovery     │      │  Claude Recovery   │     │  Human-in-the-  │
      │  Confidence    │      │  Agent (Agentic)   │     │  Loop Gateway   │
      │  Score v2      │      │                    │     │                 │
      │  (threat-      │      │  Assess → Plan →   │     │  Review plan    │
      │   weighted)    │      │  Verify → Present  │     │  NL adjustment  │
      └───────────────┘      │  → Execute         │     │  Approve/reject │
                              └────────────────────┘     └─────────────────┘
```

---

## 5. Revised Implementation Phases

### Phase 1: Foundation + OCSF (5-6 weeks)
Everything from original Phase 1, PLUS:
- [ ] OCSF event schema definitions (subset relevant to recovery)
- [ ] `threat_signals` table for ingested security events
- [ ] Webhook endpoint for SIEM alert ingestion
- [ ] Threat exposure score on `user_context` (updated from SIEM signals)

### Phase 2: Signal Enrichment + Medallion (4-5 weeks)
Everything from original Phase 2, PLUS:
- [ ] Bronze/Silver/Gold materialized views
- [ ] Silver layer: cross-reference backup state with threat timeline
- [ ] Gold layer: pre-computed MVB recovery plan (refreshed every 6 hours)
- [ ] Recovery readiness score v2 (weighted by criticality + threat state)

### Phase 3: Threat-Informed Recovery (5-6 weeks)
Everything from original Phase 3, PLUS:
- [ ] Threat-informed recovery priority formula
- [ ] "Clean point" detection: find last backup before compromise timestamp
- [ ] Recovery plan includes threat context ("why this order")
- [ ] Blast radius analyzer enriched with SIEM correlation

### Phase 4: Claude Recovery Agent (6-8 weeks)
Redesigned around multi-stage verification:
- [ ] Claude API integration with recovery-focused system prompt
- [ ] Stage 1: Situation Assessment agent (blast radius + org context)
- [ ] Stage 2: Plan Generation agent (phased recovery with reasoning)
- [ ] Stage 3: Self-Verification agent (logical consistency check)
- [ ] Stage 4: Human-in-the-Loop UI (NL adjustment, approve/reject)
- [ ] Stage 5: Monitored Execution (anomaly detection during recovery)
- [ ] Agent audit trail (full decision chain for compliance)

### Phase 5: Integrations + Advanced (Ongoing)
- [ ] Lakewatch connector (consume OCSF events from Databricks)
- [ ] CrowdStrike AgentWorks integration (recovery agent in Falcon ecosystem)
- [ ] Microsoft Defender alert integration
- [ ] Predictive recovery: ML model that predicts blast radius from early signals
- [ ] Cross-tenant MVB for MSP deployments

---

## 6. Competitive Positioning After These Changes

| Capability | Rubrik | Lakewatch | CrowdStrike | KavachIQ (Revised) |
|-----------|--------|-----------|-------------|-------------------|
| Org context | Admin-defined VIP | SIEM enrichment | Threat graph | Auto-detected + SIEM-enriched |
| Threat detection | No | Yes (core) | Yes (core) | Via SIEM integration |
| Backup/recovery | Yes (core) | No | No | Yes (core) |
| Threat-informed recovery | No | N/A | N/A | **Yes (unique)** |
| Pre-computed recovery plans | No | N/A | N/A | **Yes (unique)** |
| Clean point detection | Basic | N/A | N/A | **Threat-timeline aware** |
| Agentic recovery | Emerging | Agent Bricks | Charlotte AI | **Claude multi-stage verification** |
| Open schema | Proprietary | OCSF | Proprietary | **OCSF-compatible** |
| Human-in-the-loop | Review plan | Analyst command | Bounded autonomy | **NL adjustment + approval** |

### The Unique Differentiator

**KavachIQ becomes the only product that combines:**
1. Organizational context (who matters)
2. Threat intelligence (what happened)
3. Backup state (what's recoverable)
4. Agentic reasoning (what to do about it)

Rubrik has 1 + 3 but not 2.
Lakewatch has 1 + 2 but not 3.
CrowdStrike has 2 but not 1 or 3.

**Only KavachIQ has all four.** This is the moat.

---

## Sources

### Databricks Lakewatch
- [Databricks Press Release: Lakewatch Launch](https://www.databricks.com/company/newsroom/press-releases/databricks-enters-security-market-launch-lakewatch-new-open-agentic)
- [Databricks Blog: Lakewatch Announcement](https://www.databricks.com/blog/databricks-announces-lakewatch-new-open-agentic-siem)
- [CNBC: Databricks enters cybersecurity market](https://www.cnbc.com/2026/03/24/databricks-cybersecurity-lakewatch-ipo.html)
- [TechCrunch: Databricks buys Antimatter and SiftD](https://techcrunch.com/2026/03/24/databricks-buys-two-startups-lakewatch-antimatter-siftd-ai-security/)

### Anthropic Cybersecurity
- [Anthropic: Claude Code Security](https://www.anthropic.com/news/claude-code-security)
- [Anthropic: Building AI Cyber Defenders](https://www.anthropic.com/research/building-ai-cyber-defenders)
- [Accenture + Anthropic Cyber.AI](https://newsroom.accenture.com/news/2026/accenture-and-anthropic-team-to-help-organizations-secure-scale-ai-driven-cybersecurity-operations)
- [CrowdStrike Charlotte AI AgentWorks](https://www.crowdstrike.com/en-us/press-releases/crowdstrike-launches-charlotte-ai-agentworks-ecosystem-for-building-secure-agents/)
- [Fortune: Anthropic Mythos leak](https://fortune.com/2026/03/26/anthropic-says-testing-mythos-powerful-new-ai-model-after-data-leak-reveals-its-existence-step-change-in-capabilities/)
