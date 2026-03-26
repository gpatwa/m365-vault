# Shieldio — Product Journey Plan v3.2

## Two Connected Journeys

### Journey 1: Onboarding → Simulated Attack → Recovery (10 minutes)
**Purpose:** Customer EXPERIENCES the full cyber recovery lifecycle firsthand.
**Duration:** First 10 minutes after signup
**Emotion:** "I just lived through a ransomware attack and recovered. This product saves my business."

### Journey 2: Day-to-Day Operations → M365 Gaps (Ongoing)
**Purpose:** Daily value that M365 native features cannot provide.
**Duration:** Every day after onboarding
**Emotion:** "I use this every day. M365 can't do what Shieldio does."

**The key insight:** Journey 1 creates the emotional connection ("I need this"). Journey 2 creates the daily habit ("I can't live without this").

---

## Journey 1: Onboarding → Simulated Attack → Recovery

The customer doesn't just SET UP backup — they EXPERIENCE the full 6-phase cyber recovery story. By the end, they've seen with their own eyes how Shieldio protects them.

### Act 1: PROTECT (Steps 1-3, ~4 minutes)

**Step 1: Welcome + Connect (1 minute)**
- Welcome banner: "Let's protect your M365 data — and then test it."
- Guided checklist:
  - [ ] Connect your M365 tenant
  - [ ] Discover your workloads
  - [ ] Run your first backup
  - [ ] Experience a simulated recovery
  - [ ] See your daily operations
- Onboarding wizard: Enter credentials → auto-test → auto-discover

**Step 2: Discover (1 minute)**
- Auto-discovery shows: "Found 6 mailboxes, 8 SharePoint sites, 3 Teams, 188 Entra ID objects"
- Visual: workload cards animate in one by one
- Permission check: all green checkmarks
- "Protect All" one-click button

**Step 3: First Backup (2 minutes)**
- Real-time backup progress with live item count
- "Backing up Alex Johnson's mailbox... 47 emails, 12 events, 3 contacts..."
- Progress bar fills across each workload
- **Completion celebration**: confetti/success animation
- "Your first backup is complete! 530 items protected across 5 workloads."
- 6-phase status shows: ✅ PROTECT — Active

### Act 2: SIMULATE ATTACK (Steps 4-5, ~3 minutes)

**Step 4: Simulated Anomaly (1 minute)**
- Transition screen: "Now let's see what happens when things go wrong..."
- Dashboard shifts to "Simulation Mode" (subtle amber border)
- ⚠️ **ANOMALY ALERT** fires on dashboard:
  - "Critical: 1,847 OneDrive files renamed to .encrypted extension"
  - "Exchange: 340 emails deleted in bulk across 3 mailboxes"
  - "Entra ID: 2 Conditional Access policies modified"
- Alert banner: dramatic, full-width, red gradient
- Health score drops: 100 → 23
- Smart Engine shows: "Anomaly detected at 2:47 PM. Blast radius: 3 workloads, 2,187 items."

**Step 5: Incident Assessment (2 minutes)**
- Guided walk-through of the DETECT → RESPOND flow:
  - **DETECT**: "Here's what our AI detected. Click to see the blast radius."
  - Blast radius page: visual showing affected workloads, users, items
  - Timeline: "2:47 PM — first encrypted file, 2:48 PM — mass rename started, 2:49 PM — Shieldio detected"
  - **RESPOND**: "Shieldio auto-paused new backups to preserve the clean point."
  - Clean restore point identified: "Last clean snapshot: 2:45 PM (2 minutes before attack)"
  - "In a real attack, this is where you'd start recovery. Let's do it now."

### Act 3: RECOVER + VERIFY (Steps 6-7, ~3 minutes)

**Step 6: Recovery Execution (2 minutes)**
- Recovery wizard launches (pre-filled from simulation):
  - Scope: All 3 affected workloads
  - Restore point: 2:45 PM (last clean)
  - Preview: "2,187 items will be restored"
- Customer clicks "Start Recovery"
- **Live progress**:
  - "Restoring OneDrive... 847 of 1,847 files (46%)"
  - "Restoring Exchange... 340 emails restored ✅"
  - "Restoring Entra ID... 2 policies restored ✅"
- Completion: "Recovery complete! 2,187 items restored."

**Step 7: Verification (1 minute)**
- Auto-verification runs:
  - "Verifying checksums... 2,187 of 2,187 match ✅"
  - "Item count validation: 100% ✅"
  - "No data loss detected ✅"
- **Recovery certification**: green badge on dashboard
- Health score recovers: 23 → 100
- 6-phase status: all ✅

### Act 4: TRANSITION (Step 8, ~1 minute)

**Step 8: From Crisis to Daily Value**
- Simulation mode ends: "That was simulated. But your real protection is live."
- Transition screen:
  - "Your 6-phase cyber protection is active 24/7."
  - "Now let's show you what you'll use every day..."
  - "Things that Microsoft 365 simply cannot do."
- Button: "Explore Daily Operations →"

---

## Journey 2: Day-to-Day Operations — "What M365 Can't Do"

After the simulated attack experience, the customer transitions to daily operations. Each feature is framed against what M365 natively lacks.

### Dashboard: Daily Value Widget

A persistent widget on the dashboard showing:

```
┌─ Why You Need Shieldio (M365 Can't Do This) ──────────────┐
│                                                              │
│  📧 Exchange: Recover emails up to 365 days                 │
│     M365 limit: 28 days, then gone forever                  │
│                                                              │
│  📁 OneDrive: Point-in-time restore to any snapshot          │
│     M365 limit: recycle bin only, no point-in-time           │
│                                                              │
│  🌐 SharePoint: Full site restore with all versions          │
│     M365 limit: recycle bin, versions lost                   │
│                                                              │
│  💬 Teams: Chat and message recovery                         │
│     M365 limit: no backup, no recovery                       │
│                                                              │
│  🔑 Entra ID: Config backup + drift detection                │
│     M365 limit: no configuration backup at all               │
│                                                              │
│  🛡️ This week: 47 items recovered, 3 anomalies detected     │
└──────────────────────────────────────────────────────────────┘
```

### Contextual "M365 Can't Do This" Hints

On each workload page, a subtle info banner:

| Page | Hint |
|------|------|
| Exchange | "M365 keeps deleted emails for 28 days. Shieldio keeps them for up to 365 days." |
| OneDrive | "M365 has no point-in-time restore. Shieldio lets you restore to any backup snapshot." |
| SharePoint | "M365 recycle bin loses document versions. Shieldio preserves every version in every snapshot." |
| Teams | "M365 has no Teams chat recovery. Shieldio backs up all messages via Export API." |
| Entra ID | "M365 doesn't backup Conditional Access policies. Shieldio backs up 12 Entra ID object types." |
| Dashboard | "M365 has no backup health dashboard. Shieldio monitors everything with AI-powered anomaly detection." |

### Daily Scenario Flows

**Scenario 1: "I accidentally deleted an email" (most common)**
```
User → Self-Restore page → Search "budget email" → Find it in backup from 3 months ago
→ Preview content → Click Restore → "Email restored to your Inbox" ✅
Time: 30 seconds
M365: Would have been unrecoverable (beyond 28-day limit)
```

**Scenario 2: "Admin deleted wrong SharePoint site"**
```
Admin → SharePoint page → See deleted site in list → Browse snapshots
→ Select point-in-time → Preview site contents → Restore entire site ✅
Time: 2 minutes
M365: Recycle bin only, no point-in-time, versions lost
```

**Scenario 3: "Employee left, need their files"**
```
Admin → Search "Jane Doe" → See all her backed-up data across workloads
→ Browse OneDrive files → Download ZIP or restore to manager ✅
Time: 5 minutes
M365: OneDrive deleted 30 days after account removal
```

**Scenario 4: "Legal needs old data for audit"**
```
Admin → Command palette → Search across all historical backups
→ Find emails/files from 6 months ago → Export as .eml/.pst ✅
Time: 3 minutes
M365: Cannot search deleted/historical content
```

**Scenario 5: "Someone changed Conditional Access policies"**
```
Admin → Entra ID → Compare Snapshots → See exact diff
→ 2 policies modified, 1 deleted → Restore original policies ✅
Time: 5 minutes
M365: No Entra ID configuration backup whatsoever
```

**Scenario 6: "Teams channel messages disappeared"**
```
Admin → Teams → Team → Channel → Browse backed-up messages
→ Select date range → Restore messages with original timestamps ✅
Time: 3 minutes
M365: No Teams message recovery capability
```

**Scenario 7: "Are we compliant? Auditor asking."**
```
Admin → Security page → View compliance posture
→ Download security + compliance PDF → Share with auditor ✅
Time: 2 minutes
M365: No compliance dashboard for backups
```

**Scenario 8: "OneDrive storage spike — what happened?"**
```
Dashboard → Anomaly alert → Smart Engine shows baseline deviation
→ Identify affected user → Investigate → Resolve ✅
Time: 5 minutes
M365: No anomaly detection for storage changes
```

### Weekly Value Report (Automated Email)

```
Subject: Your Shieldio Weekly Protection Report

This week (Mar 20-27):
━━━━━━━━━━━━━━━━━━━━
✅ 1,847 new items backed up
✅ 3 items restored (would have been lost in M365)
✅ 1 anomaly detected and resolved
✅ 100% SLA compliance
✅ Health Score: 95/100

Items recovered that M365 couldn't:
  📧 Budget email from November (beyond M365 28-day limit)
  📁 Contract v2 from deleted SharePoint site
  🔑 Restored CA policy after accidental modification

Your backup saves 45 GB with 2.1x compression.
Next backup: Running now (Exchange daily cycle).
```

---

## Updated 4-Week Sprint Plan

### Sprint 1: Onboarding + Simulated Attack Experience (Week 1)
1. Post-onboarding guided checklist with progress tracking
2. Real-time backup progress with live item counts
3. First backup celebration animation
4. **Simulation mode**: trigger simulated anomaly on dashboard
5. **Simulated blast radius**: show affected items across workloads
6. **Simulated recovery**: walk through restore + verification
7. Transition screen: "From crisis to daily value"
8. Protection overview matching landing 6-phase status
9. Demo mode auto-seed with realistic attack + recovery data

### Sprint 2: Day-to-Day Value + Detection (Week 2)
10. "M365 Can't Do This" contextual hints on all workload pages
11. Dashboard daily value widget (comparison with M365 limits)
12. Self-restore: content preview before restore
13. Restore confirmation with "M365 couldn't have done this" message
14. Full-screen anomaly alert banner (real, not simulated)
15. Anomaly detail page with blast radius + timeline
16. Auto-pause backup on critical anomaly
17. Notification bell with real-time alerts

### Sprint 3: Recovery Workflows + Verification (Week 3)
18. Incident response wizard: Detect → Assess → Plan → Execute
19. Recovery wizard: scope → clean point → preview → bulk restore
20. Live recovery progress with per-item tracking
21. Post-restore verification wizard
22. Recovery report PDF (shareable for compliance/audit)
23. Cross-user restore wizard (ex-employee data)
24. Restore history: what was restored, when, by whom, what M365 couldn't do
25. E2E test: full onboarding → simulation → daily operation journey

### Sprint 4: Polish + Launch (Week 4)
26. Benchmark against real M365 tenant
27. Weekly value report template + email automation
28. Domain rename (if secured)
29. All docs updated
30. Security scan + compliance report
31. Azure deployment with release-test gate
32. 10-minute prospect demo walkthrough script
33. Prospect feedback collection mechanism

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time to "wow moment" | < 8 minutes | From signup to simulated recovery completion |
| Time to first real restore | < 2 minutes | From search to restored item |
| Daily active search | 3+ searches/day | Command palette + self-restore usage |
| Weekly value perception | "Can't go back to M365-only" | Survey after 1 week |
| Prospect demo conversion | > 50% want to continue | After 10-minute demo |
| M365 gap awareness | 5+ gaps identified | Track which hints are shown/clicked |
