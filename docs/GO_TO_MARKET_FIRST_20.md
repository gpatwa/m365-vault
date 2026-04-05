# KavachIQ — Go-to-Market: First 20 Customers

**Date: 2026-03-30 | Updated: 2026-04-03 (v5.0.0) | Status: GTM Strategy**

---

## v5.0.0 Updates (April 2026)

### Brand & Visual Identity
- **Teal/Cyan brand** (#14b8a6) replaces generic blue — modern, security-focused, distinctive
- **Geist font** + glassmorphism design inspired by Linear/Vercel/Supabase
- Landing page fully polished: hero, ransomware scenario animation, pricing, FAQ

### Product Focus: Identity + Email First
- **Onboarding focuses on Entra ID + Exchange** — the two highest-value workloads
- SharePoint, OneDrive, Teams available but collapsed under "More Workloads"
- Recovery playbook: 6-scene interactive demo with real tenant data
- Cyber attack simulation uses real mailbox names + identity objects

### Demo Experience (Updated Flow)
1. **Browse Your Tenant** — see real mailboxes and Entra ID directory
2. **Backup at a Glance** — object counts and snapshot totals
3. **Browse Your Backup** — drill into email subjects and identity items from snapshots
4. **Cyber Attack Scenario** — 3 mailboxes encrypted, MFA disabled, rogue admin injected → all recoverable
5. **Prove You Can Recover** — 100/A confidence score
6. **One-Click Recovery** — NIST plan generated + Execute button → "7 objects restored"

### Payment Acceptance (Planned)
- Stripe Billing integration for self-serve subscriptions
- 14-day free trial for Professional/Business tiers
- Self-serve upgrade/downgrade via Stripe Customer Portal
- MSP wholesale metered billing via Stripe
- See `docs/STRIPE_INTEGRATION_PLAN.md` for details

### Analytics (Planned)
- PostHog (self-hosted) for product analytics
- Plausible (self-hosted) for landing page analytics
- Microsoft Clarity for heatmaps (free)
- Google Search Console for SEO
- See `docs/ANALYTICS_ROADMAP.md` for details

### Updated Demo Script
Replace old 10-minute demo with:
1. **Landing page** (1 min) — "Your emails. Your files. Your responsibility." + Teal CTAs
2. **Tenant onboarding** (2 min) — Connect M365, security verification, discover Entra ID + Exchange
3. **Intelligence** (2 min) — Org map showing CEO → VPs → Directors → Staff priority order
4. **Recovery playbook** (4 min) — Browse tenant → Browse backup → Cyber attack → Recovery plan → Execute
5. **Pricing** (1 min) — $1.50/user, free tier available, self-hosted option

### Key Differentiators to Emphasize (Updated)
| Differentiator | v5 Proof Point |
|---|---|
| Identity-first recovery | 6-scene playbook shows Entra ID Phase 1, Exchange Phase 2 |
| Real data, not mock | Demo uses actual tenant mailboxes and identity objects |
| NIST SP 800-184 compliance | Recovery plan labeled with NIST reference |
| One-click recovery | Execute button creates real restore jobs |
| Privacy-first analytics | Self-hosted PostHog + Plausible (no Google tracking) |
| Self-serve billing | Stripe Checkout with 14-day trial |

---

## 1. Why These Segments

KavachIQ's competitive advantages that determine target segments:

| Advantage | What It Means | Who Cares Most |
|-----------|--------------|----------------|
| Entra ID config backup | No competitor does this — CA policies, roles, OAuth grants | Security-conscious orgs |
| Context-aware recovery plans | Auto-detected from Graph, no manual config | Orgs with no dedicated backup admin |
| $1.50/user | Cheapest in market with intelligence included | Budget-constrained regulated industries |
| Self-hosted option | Data sovereignty, no vendor cloud dependency | Law firms, healthcare, government |
| SOC 2 + GDPR + HIPAA + DORA | Compliance-ready out of the box | Regulated industries |
| WORM + legal hold | Immutable backups with retention locks | Law firms, finance |

**Ideal first customer**: Regulated industry, 50-300 users, uses M365, has **no third-party backup** or is **overpaying** for Veeam/Rubrik, and makes fast buying decisions (1-2 decision makers).

---

## 2. Target Segments

### Tier 1: Highest Probability (Target 8-10 customers)

#### A. Healthcare Clinics & Medical Groups (50-300 users)

**Why perfect for KavachIQ:**
- HIPAA requires backup with encryption, audit trail, and retention
- Most clinics have M365 but no third-party backup — they assume Microsoft handles it
- Entra ID backup is critical — CA policies protect patient data access
- Can't afford Rubrik ($6-10/user) but need more than recycle bin
- Decision maker: Practice administrator or IT manager (1 person, fast decision)

**Pitch:** "$1.50/user/mo for HIPAA-compliant M365 backup with encrypted storage, audit trail, and recovery plans. Your compliance officer will love you."

**How to find:**
- LinkedIn search: "IT Manager" + "Medical Group" / "Healthcare" + M365
- Local medical associations and healthcare IT groups
- HIPAA compliance consultants as referral partners
- Healthcare IT conferences and webinars

**Target: 3-4 customers**

---

#### B. Law Firms (20-200 users)

**Why perfect for KavachIQ:**
- Legal hold / WORM is a must-have (client privilege, litigation holds)
- eDiscovery search across backup data — needed for cases
- Data sovereignty matters — some firms won't use cloud-only backup (self-hosted option)
- Entra ID config backup protects privileged access to client data
- Small IT team (often 1 person or outsourced), need turnkey solution

**Pitch:** "Immutable backup with legal hold, eDiscovery search, and full audit trail. Your compliance partner already built in."

**How to find:**
- State bar association tech committees
- Legal tech conferences (LegalTech, ILTACON)
- IT consultants who serve law firms
- LinkedIn: "IT Director" + "Law Firm" / "Legal"

**Target: 3-4 customers**

---

#### C. Financial Services / Accounting Firms (50-500 users)

**Why perfect for KavachIQ:**
- SOX, SEC, FINRA all require backup + retention + audit
- Handle extremely sensitive financial data — per-tenant encryption matters
- Seasonal workloads (tax season) = need reliable recovery
- Many use M365 E3/E5 but don't have separate backup

**Pitch:** "SOC 2 + GDPR compliant backup at $1.50/user. Every admin action logged. Recovery plans pre-built. Auditors love it."

**How to find:**
- CPA associations (AICPA, state CPA societies)
- Regional accounting firm networks
- FinTech meetups and communities
- LinkedIn: "IT Manager" + "CPA" / "Accounting" / "Financial Advisory"

**Target: 2-3 customers**

---

### Tier 2: High Value Multipliers (Target 5-8 customers)

#### D. MSPs Managing 5-20 M365 Tenants

**Why perfect for KavachIQ:**
- One MSP = 5-20 end customers overnight (multiplier effect)
- Already selling M365, backup is a natural add-on service
- Multi-tenant architecture fits their operating model
- White-label / reseller opportunity at margin
- They hate Veeam's complexity and Rubrik's price

**Pitch:** "Add M365 backup to your managed services stack. $1.50/user wholesale, multi-tenant, your branding. Sell at $3-5/user, keep the margin."

**How to find:**
- MSP conferences (MSP Summit, IT Nation Connect, DattoCon)
- Reddit r/msp — answer backup questions, offer partnership
- Local IT networking groups and meetups
- ConnectWise / Datto / NinjaOne community forums

**Target: 2-3 MSPs (= 10-40 end-customer tenants)**

---

#### E. Education (K-12 Districts, Small Colleges)

**Why perfect for KavachIQ:**
- FERPA compliance requires data protection
- Budget-constrained — $1.50/user is very attractive vs $5+ alternatives
- Large user counts (500+ teachers/staff) but small IT teams
- Often have M365 A3/A5 but no backup strategy at all

**Pitch:** "FERPA-ready M365 backup for your entire district. Free for up to 25 users, $1.50/user after that."

**How to find:**
- State education technology associations
- EDUCAUSE conferences and mailing lists
- School district IT director LinkedIn groups
- E-Rate procurement cycles

**Target: 2-3 districts/colleges**

---

#### F. Cybersecurity-Conscious Startups (50-200 users)

**Why perfect for KavachIQ:**
- Already pursuing SOC 2 for their own customers
- Tech-savvy — appreciate open-source, self-hosted angle
- Decision cycle is fast (CTO decides in 1 meeting)
- Anomaly detection + recovery intelligence appeals to security-minded buyers
- GitHub community can drive organic adoption

**Pitch:** "Open-source M365 backup with anomaly detection. Self-host on your infrastructure. SOC 2 ready. $1.50/user."

**How to find:**
- GitHub stars → developer advocates → their companies become customers
- HackerNews, Reddit r/sysadmin, r/azure
- Y Combinator / TechStars alumni networks
- Startup security communities (SOC 2 Slack groups)

**Target: 2-3 startups**

---

### Tier 3: Long-Term (After 20 customers)

| Segment | Why Later | Trigger |
|---------|-----------|---------|
| Enterprise (1,000+ users) | Need case studies, longer sales cycle | After 10+ happy customers |
| Government | FedRAMP/StateRAMP needed | After compliance certifications |
| Manufacturing | Less M365-dependent, lower urgency | When horizontal expansion makes sense |
| Multinational | Multi-region deployment needed | After Hybrid Backup (Q3 2026) |

---

## 3. Revenue Model: First 20 Customers

| Segment | Customers | Avg Users | Tier | Monthly Revenue |
|---------|-----------|-----------|------|----------------|
| Healthcare clinics | 4 | 100 | Professional $1.50 | $600 |
| Law firms | 3 | 80 | Business $3.00 | $720 |
| Financial/Accounting | 3 | 150 | Professional $1.50 | $675 |
| MSPs (managing tenants) | 3 | 300 total | Professional $1.50 | $450 |
| Education | 2 | 200 | Professional $1.50 | $600 |
| Startups | 3 | 75 | Professional $1.50 | $338 |
| **Total** | **18** | **~2,500 users** | | **$3,383/mo** |

**Annual run rate: ~$40K**
**Infrastructure cost: ~$445/mo** (shared medium tier, optimized)
**Net margin: ~87%**

---

## 4. Go-to-Market Channels

### Channel 1: Direct Outreach (Weeks 1-4)

| Step | Action | Volume |
|------|--------|--------|
| 1 | LinkedIn: Search IT managers at healthcare/legal/finance orgs (50-300 employees, M365) | 50 prospects |
| 2 | Personalized connection request + message | 50 messages |
| 3 | Message: "Do you have independent backup beyond Microsoft's recycle bin?" | Open-ended, non-salesy |
| 4 | Offer free 25-user tier to prove value | Convert to trial |
| 5 | Run first backup demo with their data (10 min) | Convert to paid |

**Expected conversion**: 50 outreach → 10 responses → 5 demos → 2-3 customers

### Channel 2: MSP Partnerships (Weeks 2-6)

| Step | Action |
|------|--------|
| 1 | Post in r/msp: "Open-source M365 backup at $1.50/user — looking for MSP beta partners" |
| 2 | Attend local IT networking events / virtual MSP meetups |
| 3 | Offer first 3 months free for MSP partners |
| 4 | MSP sells to their clients at $3-5/user, KavachIQ provides platform |
| 5 | Provide MSP co-branded marketing materials |

**Expected conversion**: 10 MSP conversations → 3 partnerships → 10-40 end tenants

### Channel 3: Compliance Consultants as Referral Partners (Weeks 3-8)

| Step | Action |
|------|--------|
| 1 | Identify 10 HIPAA compliance consultants on LinkedIn |
| 2 | Offer: "Every clinic you audit has a backup gap. We fix it for $1.50/user." |
| 3 | Referral fee: 10-20% of first year revenue |
| 4 | Do the same with SOC 2 auditors and GDPR consultants |
| 5 | Provide compliance-focused one-pager for their client presentations |

**Expected conversion**: 5 consultant partnerships → 5-10 referred customers/year

### Channel 4: Content & Community (Ongoing)

| Content | Target Audience | Distribution |
|---------|----------------|--------------|
| "Why Microsoft's recycle bin is not HIPAA-compliant backup" | Healthcare IT | Blog, LinkedIn, HIPAA forums |
| "The $4.5M ransomware recovery mistake: no recovery plan" | CISOs, CTOs | Blog, HackerNews, LinkedIn |
| "How to get SOC 2 compliant M365 backup in 10 minutes" | Startups | Blog, Reddit r/sysadmin |
| "M365 backup for law firms: legal hold + eDiscovery" | Legal IT | Blog, legal tech forums |
| "Why your MSP should add M365 backup (margin calculator)" | MSPs | Reddit r/msp, MSP forums |

---

## 5. Sales Process

### For Direct Sales (Healthcare, Legal, Finance)

```
Week 1: LinkedIn connection + qualifying message
Week 2: 15-min discovery call ("What's your M365 backup today?")
Week 3: 10-min live demo with their data (demo account or free tier)
Week 4: Proposal ($1.50-3.00/user, annual or monthly)
Week 5: Close + onboard (OAuth connect, first backup same day)
```

**Average deal cycle: 3-5 weeks**
**Average deal size: $150-450/mo ($1,800-5,400/yr)**

### For MSP Partnerships

```
Week 1: Initial conversation (r/msp, event, LinkedIn)
Week 2: Technical demo + multi-tenant walkthrough
Week 3: Partner agreement (wholesale pricing, SLA)
Week 4: Pilot with 2-3 of their clients
Week 6-8: Full rollout across MSP client base
```

**Average deal cycle: 6-8 weeks**
**Average MSP value: $450-1,500/mo across their clients**

---

## 6. Competitive Objection Handling

| Objection | Response |
|-----------|----------|
| "We already have Veeam" | "Does Veeam back up your Entra ID config? If an attacker disables MFA, can Veeam roll it back? We can — and at $1.50 vs $2.00/user." |
| "Microsoft handles our backup" | "Microsoft's recycle bin is 93 days. If ransomware encrypts your mailboxes, there's no recovery plan — just a support ticket. We build recovery plans from your org chart automatically." |
| "We can't afford another tool" | "At $1.50/user, a 100-person org pays $150/mo. A single ransomware incident averages $4.5M. The ROI is infinite." |
| "Is it enterprise-ready?" | "AES-256-GCM encryption, SOC 2 + HIPAA + GDPR + DORA compliant, WORM immutable storage, full audit trail. We're built for regulated industries." |
| "We'll evaluate in Q4" | "Free for 25 users. Set it up in 10 minutes, prove it works, then budget for next quarter with evidence." |
| "What about Teams/Entra ID?" | "We're one of the few that backs up Teams chats AND Entra ID configuration. That includes Conditional Access policies, directory roles, and OAuth grants. No competitor covers all of this." |

---

## 7. Week 1-4 Action Plan

| Week | Monday | Tuesday-Thursday | Friday |
|------|--------|-----------------|--------|
| **1** | LinkedIn: Connect with 20 healthcare IT managers | Send 20 personalized messages. Post in r/msp. | Follow up on responses. Identify 5 HIPAA consultants. |
| **2** | Schedule discovery calls from Week 1 responses | Run 3-5 demo calls. Connect with 15 law firm IT contacts. | Publish blog: "Microsoft recycle bin isn't HIPAA backup" |
| **3** | LinkedIn: Connect with 15 finance/accounting IT | Run demos. Contact 5 HIPAA consultants for partnership. | Follow up all open threads. Post in r/sysadmin. |
| **4** | Close first 2-3 customers. Onboard same day. | Continue demos. Formalize first MSP partnership. | Week 4 review: pipeline, conversions, adjust targeting. |

**Target by end of Week 4**: 3-5 paying customers, 2 MSP partnerships in pilot, 3 compliance consultant relationships.

---

## 8. Metrics to Track

| Metric | Week 4 Target | Month 3 Target |
|--------|--------------|----------------|
| LinkedIn outreach sent | 50 | 200 |
| Discovery calls completed | 10 | 40 |
| Demos given | 5 | 20 |
| Free tier signups | 8 | 30 |
| Paying customers | 3-5 | 15-20 |
| MSP partnerships | 2 | 5 |
| MRR | $500 | $3,000+ |
| ARR run rate | $6K | $36K+ |

---

## 9. Pricing Quick Reference

| Tier | Price | Best For |
|------|-------|----------|
| **Community** | Free forever | 25 objects, 3 workloads — trial/POC |
| **Professional** | $1.50/user/mo | SMB, healthcare clinics, startups — all 5 workloads, 90-day retention |
| **Business** | $3.00/user/mo | Law firms, finance — Org Context, MVB Plans, 1-year retention |
| **Enterprise** | $5.00/user/mo | Large orgs, MSP resale — Agentic Recovery, WORM, eDiscovery |

---

## 10. Demo Script (10 minutes) — Updated v5

| Minute | Action | What They See |
|--------|--------|---------------|
| 0-1 | Show landing page | Teal brand, "Your emails. Your files. Your responsibility." |
| 1-2 | Login → Onboard with tenant | Connect M365, security verification (OAuth, encryption, per-tenant isolation) |
| 2-3 | Discovery | Entra ID + Exchange pre-selected (2 priority workloads), 3 more available |
| 3-4 | Intelligence map | CEO (95) → VPs (82-88) → Directors → Staff — auto-scored from Graph |
| 4-5 | Recovery playbook: Browse tenant | Real mailboxes with names, Entra ID directory with counts |
| 5-6 | Recovery playbook: Browse backup | Actual email subjects from snapshots, identity objects backed up |
| 6-7 | Recovery playbook: Cyber attack | 3 mailboxes "ENCRYPTED", MFA disabled, rogue admin → all "RESTORED" |
| 7-8 | Recovery playbook: Execute | NIST plan → Phase 1 Identity, Phase 2 Email → "7 objects restored" |
| 8-9 | Show confidence + pricing | 100/A confidence score. "$1.50/user. Free tier. Self-hosted option." |
| 9-10 | Close | "Want to connect your tenant? 14-day free trial. Takes 2 minutes." |

**Key phrases for the demo:**
- "Identity first. If attackers have admin access, restoring data is pointless."
- "This is your real data — not a simulation. These are your actual mailboxes."
- "Pre-computed NIST recovery plan. When ransomware hits at 2am, recovery starts instantly."
- "Self-hosted analytics. We don't even track your product usage on third-party servers."
