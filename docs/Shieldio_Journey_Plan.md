# Shieldio — Product Journey Plan v3.1

## Two Distinct Journeys

### Journey 1: Onboarding (Cyber Recovery Focus)
**Purpose:** Show why you need Shieldio. The dramatic value proposition.
**Duration:** First 10 minutes → first 24 hours
**Emotion:** "I'm protected now. If ransomware hits, I can recover."

### Journey 2: Day-to-Day Operations
**Purpose:** Show what M365 can't do. Daily value that justifies the subscription.
**Duration:** Every day after onboarding
**Emotion:** "I use this every day. I can't go back to not having it."

---

## Journey 1: Onboarding — Cyber Recovery Story

The onboarding experience walks the customer through the 6-phase cyber recovery lifecycle. By the end, they've seen the full protection story and their data is backed up.

### Step 1: Landing Page (30 seconds)
- Animated cyber recovery story plays: PROTECT → MONITOR → DETECT → RESPOND → RECOVER → VERIFY
- Trust badges: AES-256, SOC 2 Ready, GDPR
- CTA: "Start Free" → Register

### Step 2: First Login → Welcome Dashboard (1 minute)
- Welcome banner: "Let's protect your M365 data in 5 minutes"
- Guided checklist appears:
  - [ ] Connect your M365 tenant
  - [ ] Discover your workloads
  - [ ] Run your first backup
  - [ ] Verify protection status
- Empty dashboard with placeholder cards showing what will populate

### Step 3: Connect Tenant (2 minutes)
- Onboarding wizard Step 1: Enter tenant ID + credentials
- Auto-test connection → green checkmark
- Auto-discover workloads → show counts (6 mailboxes, 8 SharePoint sites, etc.)
- Permission check → show what's granted vs missing
- "Fix Permissions" one-click button

### Step 4: First Backup (3 minutes)
- Wizard Step 2: Choose SLA policy (Daily recommended)
- One-click "Protect All" → assigns policy to all discovered objects
- First backup triggers automatically
- **Real-time progress**: "Backing up Alex Johnson's mailbox... 47 items..."
- **Completion celebration**: "Your first backup is complete! 230 items protected."
- Checklist updates: ✅ First backup complete

### Step 5: Protection Overview (1 minute)
- Dashboard populates with real data:
  - Health Score: 100 (all green)
  - Protection: 29/29 objects (100%)
  - Last backup: "Just now"
  - Workload cards with item counts
- **Key message**: "Your 6-phase protection is now active"
- Show the 6 phases as status indicators:
  - ✅ PROTECT — Backups running
  - ✅ MONITOR — AI learning baselines (3 of 7 days)
  - ⏳ DETECT — Thresholds setting (needs baseline data)
  - ⏳ RESPOND — Ready when needed
  - ✅ RECOVER — Restore available
  - ✅ VERIFY — Validation ready

### Step 6: Guided Tour of Recovery (2 minutes)
- Product tour highlights:
  1. "This is your Health Score — it drops if something goes wrong"
  2. "Click any workload to drill into backup details"
  3. "Search works across all backups — try searching for any email or file"
  4. "If we detect an anomaly, you'll see an alert right here"
  5. "Recovery dashboard shows your readiness score"
  6. "Self-restore lets your users recover their own deleted items"

---

## Journey 2: Day-to-Day Operations — "What M365 Can't Do"

After onboarding, the product should surface daily value that demonstrates why native M365 features are not enough. Each scenario shows a real problem that M365 cannot solve.

### Daily Scenario 1: "Someone deleted important emails" (MOST COMMON)
**M365 limitation:** Deleted items recoverable for 14 days (recycle bin), 14 more days (admin recovery). After 28 days: GONE.
**Shieldio:** Search across all backup snapshots → find the email from 3 months ago → restore in 30 seconds.
**UI touchpoint:** Self-Restore page, Command Palette search

### Daily Scenario 2: "Admin accidentally deleted a SharePoint site"
**M365 limitation:** Deleted sites stay in recycle bin for 93 days, but document versions are lost. No point-in-time.
**Shieldio:** Browse SharePoint snapshots → pick the exact point in time → restore entire site with all versions.
**UI touchpoint:** SharePoint workload page → snapshot list → restore

### Daily Scenario 3: "Employee left — need their OneDrive files"
**M365 limitation:** OneDrive gets deleted 30 days after account removal. Manager access is complicated.
**Shieldio:** Search by employee name → browse their backed-up OneDrive → restore to manager or download as ZIP.
**UI touchpoint:** Self-Restore search, OneDrive workload page

### Daily Scenario 4: "Legal needs old emails for compliance audit"
**M365 limitation:** M365 audit log retains for 90 days (E3) or 1 year (E5). No search across deleted content.
**Shieldio:** Search across all historical backups → export as .eml or .pst → provide to legal team.
**UI touchpoint:** Command Palette search, Export functionality

### Daily Scenario 5: "Someone changed Conditional Access policies"
**M365 limitation:** M365 does NOT backup Entra ID configuration. No way to see what changed or roll back.
**Shieldio:** Entra ID snapshot diff → see exactly what changed between two points → restore previous policy.
**UI touchpoint:** Entra ID page → Compare snapshots

### Daily Scenario 6: "Teams channel messages disappeared"
**M365 limitation:** No native Teams chat/message backup. Deleted messages are unrecoverable after retention period.
**Shieldio:** Teams backup via Export API → browse backed-up messages → restore via Migration API with original timestamps.
**UI touchpoint:** Teams workload page → channel browse → restore

### Daily Scenario 7: "Are we compliant? Auditor is asking."
**M365 limitation:** M365 has no compliance dashboard for backups. No way to prove data protection posture.
**Shieldio:** Security page shows encryption status, WORM locks, compliance mapping (SOC 2, GDPR, HIPAA). Downloadable report.
**UI touchpoint:** Security page, Reports page

### Daily Scenario 8: "OneDrive storage spike — what happened?"
**M365 limitation:** M365 admin center shows storage but no anomaly detection, no trend analysis.
**Shieldio:** Smart Engine detects the anomaly, sends alert, shows baseline comparison, identifies affected users.
**UI touchpoint:** Dashboard anomaly alert, Smart Engine page

---

## How to Surface "M365 Can't Do This" in the Product

### Option 1: Contextual Hints (Subtle)
On each page, show a small info banner:
- Exchange page: "💡 M365 only keeps deleted emails for 28 days. Shieldio keeps them for 365 days."
- SharePoint page: "💡 M365 can't do point-in-time site restore. Shieldio can restore to any backup snapshot."
- Entra ID page: "💡 M365 doesn't back up Conditional Access policies. Shieldio backs up 12 Entra ID object types."
- Teams page: "💡 M365 has no Teams chat recovery. Shieldio backs up all channel messages and 1-to-1 chats."

### Option 2: Comparison Widget (Dashboard)
A small widget on the dashboard showing:
```
What Shieldio does that M365 can't:
├── 📧 Exchange: 365-day recovery (vs M365's 28 days)
├── 📁 OneDrive: Point-in-time restore (vs no PIT in M365)
├── 🌐 SharePoint: Full site restore with versions (vs recycle bin only)
├── 💬 Teams: Chat/message backup (vs no backup in M365)
└── 🔑 Entra ID: Config backup + diff (vs nothing in M365)
```

### Option 3: Weekly Value Report (Email)
Automated weekly email showing:
- "This week Shieldio protected 1,847 new items"
- "3 items were restored that M365 couldn't have recovered"
- "Your health score: 95 (anomaly detected and resolved)"
- "Compliance: 100% SLA adherence, 45 snapshots WORM-locked"

---

## Updated Sprint Plan

### Sprint 1: Onboarding + Self-Service (Week 1)
Focus: The "wow" moment — customer connects, backs up, and restores within 10 minutes.

1. Post-onboarding guided checklist
2. Real-time backup progress with item counts
3. First backup celebration state
4. Protection overview matching landing page 6-phase visual
5. Self-restore content preview before restore
6. Restore confirmation with success notification
7. "M365 can't do this" contextual hints on workload pages
8. Demo mode with realistic scenario data
9. Product tour reordered for cyber recovery + daily value

### Sprint 2: Detection + Response (Week 2)
Focus: When something goes wrong, the customer knows immediately and has a clear path forward.

10. Full-screen anomaly alert banner on dashboard
11. Anomaly detail page: blast radius, timeline, affected objects
12. Auto-pause backup scheduler on critical anomaly
13. Clean restore point identification (last snapshot before incident)
14. Notification bell with real-time alerts
15. Email/webhook notification triggers

### Sprint 3: Recovery + Verification (Week 3)
Focus: Complete recovery workflow — from incident to verified restoration.

16. Incident response wizard: Detect → Assess → Plan → Execute
17. Recovery wizard: scope → clean point → preview → bulk restore
18. Live recovery progress with per-item tracking
19. Post-restore verification wizard
20. Recovery report PDF (shareable)
21. E2E test: full journey from onboard to verified recovery

### Sprint 4: Polish + Launch (Week 4)
Focus: Production-ready for design partner demos.

22. Benchmark against real M365 tenant
23. Performance page with verified metrics
24. Domain rename (if secured)
25. Alembic database migrations
26. All docs updated
27. Security scan + compliance report
28. Azure deployment with release-test gate
29. 10-minute prospect demo walkthrough script
30. Weekly value report template

---

## Metrics to Track

| Metric | Target | How |
|--------|--------|-----|
| Time to first backup | < 5 minutes | Measure from login to first snapshot |
| Time to first restore | < 1 minute | Measure from search to restored item |
| Prospect demo completion | 10 minutes | Scripted walkthrough |
| "Aha moment" | Step 5 (protection overview) | Where prospects say "I get it" |
| Daily active usage | Self-restore search | Track search queries per day |
| Weekly value delivered | Items recovered | Count restores that M365 couldn't do |
