# Founder Demo Script — KavachIQ for Microsoft 365

**Audience**: Microsoft 365 admins, IT/security leaders, procurement-aware buyers
**Format**: 30-minute first call (default) · 60-minute deeper walkthrough (extension)
**Use case**: Founder-led or technical-seller use. Adapt language to the buyer in front of you.

> Strategic anchor: KavachIQ is the **identity-first cyber recovery platform for Microsoft Entra and Microsoft 365**. Not a generic backup product. Not a broad cyber suite. Stay on this line.

---

## Pre-call prep (5 minutes before)

- Open these in browser tabs:
  - `https://kavachiq.com/welcome` (homepage)
  - `https://kavachiq.com/tour` (live product tour)
  - `https://kavachiq.com/scenarios/compromised-global-admin` (the strongest scenario)
  - `https://kavachiq.com/security` (for security/procurement signals)
  - `https://kavachiq.com/overview` (post-call follow-up URL)
- Skim the prospect's tenant context if known: M365 size, regulated industry, recent incidents in the news for their sector.
- Have the contact panel ready: `hello@kavachiq.com`, `security@kavachiq.com`, `sales@kavachiq.com`.

---

## Opening framing (2 minutes)

Use one of these openers depending on the buyer.

**For a Microsoft 365 admin or Head of IT:**
> "Most Microsoft 365 incidents are not clean data-loss events. They mix identity changes, destructive admin actions, and ambiguous blast radius. KavachIQ exists to handle that recovery, and to handle it identity-first. I want to show you how that works in 30 minutes, and then leave time for your questions."

**For a security leader (CISO, security architect):**
> "When ransomware or a privileged identity compromise hits a Microsoft 365 tenant, the first 30 minutes decide everything. The hard part is not 'do I have a backup?' It is 'what changed, who is affected, what do I restore first, and how do I know we are actually back online?' That is the gap KavachIQ closes. I have a 30-minute walkthrough planned. Tell me up front if there is a specific incident scenario you want me to focus on."

**For a procurement-aware buyer (CIO, IT Director, VP):**
> "KavachIQ is purpose-built for Microsoft 365 cyber recovery. Identity first, then data, then verified business recovery. I will keep this practical: a quick framing, a live walkthrough of the recovery workflow, and the security and trust signals your procurement team will care about. Stop me at any point."

**Avoid in the opener:**
- "AI-powered..." (we are not pitching AI)
- "Open source..." (not the GTM)
- "Free for 25 users..." (no PLG motion)
- "Microsoft doesn't back up your data..." (anti-Microsoft framing is off-strategy)
- Hype words: revolutionary, game-changing, seamless, cutting-edge.

---

## Discovery questions (3-5 minutes)

Pick 3-4 from this list. Listen more than you talk.

**Environment:**
- Roughly how many Entra users / mailboxes / SharePoint sites in scope?
- Is your M365 tenant single-tenant, multi-geo, or part of an MSP relationship?
- Any specific regulated workloads in M365 (legal hold, retention, eDiscovery)?

**Recovery posture:**
- What does your team do today when a privileged account is compromised in Entra?
- If 1,000 mailboxes were deleted right now, how would you recover, and how confident are you in the order?
- Have you ever tried to roll back an Entra conditional access policy or OAuth grant change? How did that go?

**Stakeholders:**
- Who owns Microsoft 365 recovery in your org: IT, security, both?
- Who would be in the room for a follow-up evaluation?

**Trigger:**
- Anything specific prompting this call now: a recent incident, an audit, a vendor renewal, a new compliance requirement?

> Adjust the rest of the call based on what you hear. If they raise a specific scenario, jump straight to that scenario page.

---

## 30-minute demo flow

Total budget: ~20 minutes after opener + discovery. Use the live site, not slides.

### Section 1 · Position the problem (2 minutes)

Open `kavachiq.com/welcome`.

Hit two sections:
1. **Problem section** ("What actually breaks in a Microsoft 365 incident") — 30 seconds. Read 2-3 of the 6 cards aloud, especially the ones that match what they said in discovery.
2. **Why backup alone is not enough** — 1 minute. Land this line:
   > "Backup preserves data. Recovery is a different problem. KavachIQ focuses on the recovery problem: what changed, who is affected, what to restore first, and how to verify business recovery."

### Section 2 · Identity-first explained (3 minutes)

Stay on `/welcome`. Scroll to **Why identity-first matters**.

Walk the two-up explanation:
- Identity controls the blast radius (admins, privileged roles, conditional access, OAuth grants, group membership).
- Restore in the right order (identity → critical users → high-priority → full).

Land this line:
> "If you restore mailboxes before you restore identity, the attacker still holds Global Admin. Data recovery without identity recovery is incomplete. That is why KavachIQ restores Entra controls first, every time."

### Section 3 · How a recovery actually unfolds (4 minutes)

Scroll to the **CyberRecoveryStory** animation. Let it auto-play one cycle: Protect → Monitor → Detect → Assess → Recover → Verify.

Narrate alongside:
- Protect — identity and data state captured on a schedule, encrypted, WORM-locked.
- Monitor — baselines per tenant.
- Detect — destructive change and identity drift flagged with evidence.
- Assess — blast radius computed, recovery order generated.
- Recover — guided restore in the safest order.
- Verify — checksums, policy-active checks, sign-in tests.

Land this line:
> "These are not six features. They are six phases of one workflow. Every recovery KavachIQ runs goes through this."

### Section 4 · Walk a concrete scenario (6 minutes)

Open `kavachiq.com/scenarios/compromised-global-admin`.

This is the strongest single proof asset. Use it like a story.

1. **Hero** — read the headline. "Recovery scenario: compromised Global Admin in Microsoft 365."
2. **Incident setup** — pause on 2-3 cards: identity compromise, conditional access modified, data access expands. Tie it to the buyer's environment.
3. **Why manual recovery is hard** — read the second numbered point: "Policy drift is invisible." Most prospects nod.
4. **Six phases applied to this incident** — scroll through. Highlight the **Recover** phase: "Phase A revert privileged role assignments. Phase B restore conditional access, MFA, OAuth grants. Phase C recover critical users first."
5. **Identity-first recovery order** — quick read of the four steps.
6. **Outcomes** — land this line:
   > "We don't claim to prevent the incident. We change how your team runs the recovery and how defensibly you can sign off on being back online."

If the buyer cares more about Exchange than Entra, swap to `/scenarios/bulk-mailbox-deletion-retention-drift`. Same structure, mailbox-centric content.

If the buyer cares more about SharePoint/OneDrive, swap to `/scenarios/destructive-sharepoint-onedrive-deletion`.

### Section 5 · Security and trust (3 minutes)

Open `kavachiq.com/security`.

You don't need to walk every section. Hit three things:
1. **Tenant data handling lifecycle** — point at the six-stage strip: Connect, Capture, Store, Recover, Verify, Audit. Land:
   > "Here is what we do with tenant data, end to end. Every claim on this page is something your security team can verify."
2. **Procurement FAQ** — point out the question they are most likely about to ask. For most buyers it is "How is customer access scoped and isolated by tenant?" Open and read the answer.
3. **`security@kavachiq.com`** — name the contact path explicitly:
   > "For SOC 2 reports, DPA, or vendor-risk questionnaires, your team writes to security@kavachiq.com. Reply within one business day."

### Section 6 · Close (2 minutes)

Three asks, in order of preference:

**Best:** "What does a follow-up technical walkthrough look like with your team in the room? Who else needs to be there?"

**Good:** "Can I send you a one-page overview after this call you can forward internally? It's at kavachiq.com/overview."

**Always:** "Is there a specific incident scenario you want us to walk in the next call? We can spin the discussion around your environment instead of a generic demo."

End with the time check. If you are over 28 minutes, stop. Punctuality is part of the trust signal.

---

## 60-minute deeper walkthrough (extension)

Use this when the buyer asks for more time, when there are technical and security stakeholders together, or when procurement is on the call.

The 30-minute flow above is **section 1 of the 60-minute call**. Run it as written. Do not re-do it.

After the 30-minute close, transition with:
> "We have time. Let me go deeper on the part of this that matters most to you. I have three options."

### Option A · Deeper Entra and recovery workflow (technical, 20 min)

Stay on `kavachiq.com/welcome` and `kavachiq.com/tour`.

- Walk the Tour scene-by-scene: dashboard, criticality scoring, threat detection, identity-first recovery.
- Open `/welcome`, scroll to the "Purpose-built for Microsoft 365 recovery" pillars section. Walk the six pillars in sequence: Entra Recovery, Criticality-Based Recovery, Blast Radius Analysis, Guided Recovery Plans, M365 Data Recovery, Recovery Verification.
- Discuss the 12 Entra ID object types we capture: users, groups, role assignments, conditional access policies, OAuth grants, service principals, administrative units, named locations, app registrations, devices, domains, directory roles. Most buyers want to verify their list.
- Spend the last 5 minutes on recovery verification specifics: checksums, policy-active checks, sign-in validation, recovery report.

### Option B · Deeper security and procurement (security/risk, 20 min)

Stay on `kavachiq.com/security`.

- Walk the principles section: Microsoft-native access model, tenant-scoped by design, identity-aware recovery, enterprise controls day one.
- Walk all 8 core controls cards.
- Walk the **Tenant data handling** six-stage lifecycle in full. Pause on Store and explicitly state:
  > "Customer recovery data is stored in Microsoft Azure Storage in the region configured for the deployment. For region-specific or DPA questions, security@."
- Walk the **Compliance and review** section. Be honest: "These are mapped controls, not a SOC 2 report. The report is requested via security@."
- Walk the **Procurement FAQ** — answer 3-4 questions out loud. Let the buyer interrupt with their own.
- Close on the architecture cards: Azure deployment, control-plane / data-plane separation, Microsoft Graph, API and onboarding.

### Option C · Walk all three scenarios (operations/IR, 20 min)

Open `kavachiq.com/scenarios`.

- 5 minutes per scenario. Use the index page to introduce, then dive into each scenario page for the operational detail.
- For each, focus on the **Recovery order** section — that is the operationally interesting one for IR teams.
- Close with: "These are not the only incidents we handle. They are the patterns we walk most often. If your team has a fourth pattern, send it to us."

---

## Likely buyer questions and how to answer

**"How are you different from Veeam, Rubrik, Druva?"**
> "We are not trying to replace them. They preserve data well. KavachIQ focuses on the recovery problem on top of that, identity-first, purpose-built for Microsoft 365 and Entra. If you already have a backup vendor, we sit alongside them on the recovery side."

Do not chest-thump or claim they don't do something. Stay on category, not vendor.

**"Microsoft has Entra Backup now. Why do we need you?"**
> "Native Entra backup keeps a copy of identity configuration. KavachIQ runs the recovery workflow on top of that: blast radius assessment, recovery order, criticality scoring across users and data, and recovery verification. Microsoft is solving the storage problem. We are solving the operational recovery problem."

**"Where is our data stored? Can we choose a region?"**
> "Customer recovery data is stored in Microsoft Azure Storage in the region configured for the deployment. For specific regional requirements or a data-processing agreement, route to security@kavachiq.com."

**"Do you store our admin credentials?"**
> "No. KavachIQ uses Microsoft Entra OAuth admin consent. Your Global Admin approves scoped access, and only a tenant-scoped API token is used. Passwords are never seen or stored."

**"What about our DPA / SOC 2 report?"**
> "Both available through security@kavachiq.com. Mapping documentation is on /security. Formal artifacts route through the security contact."

**"How long is a typical deployment?"**
> "Tenant onboarding is OAuth-driven. We can show value in a recovery walkthrough on day one. Production deployment timeline depends on your change-management process more than ours."

**"Pricing?"**
> "Let's align on what is in scope first: which workloads, how many users, MSP or single-tenant. Once we agree on the shape of the deployment, I'll walk you through pricing options. The key thing is we don't price recovery intelligence as a separate add-on."

Do not lead with a price. Do not anchor low. Do not improvise tiers.

**"Can we self-host?"**
> "We deploy on Azure as a managed offering. If self-hosted is a strict requirement for you, let's talk about it separately so I understand the constraint."

Do not promote self-hosted. Do not refuse outright. Take it offline.

**"What about Agent Shield / AI agent governance?"**
> "Different product, different conversation. KavachIQ for Microsoft 365 is the recovery platform we are talking about today."

Do not blend the stories.

---

## Suggested closing / next-step ask

In order of preference:

1. **A booked technical walkthrough** with the right people in the room. Specific date and time. Specific scenario to focus on.
2. **A security/procurement intro** to security@kavachiq.com if the buyer is not the security owner.
3. **A forwardable overview** sent immediately after the call: `kavachiq.com/overview`.
4. **A scenario page sent for internal share** if a specific incident pattern resonated: `/scenarios/compromised-global-admin`, `/destructive-sharepoint-onedrive-deletion`, or `/bulk-mailbox-deletion-retention-drift`.

Always send the follow-up email within 2 hours of the call. Include:
- The overview URL: `https://kavachiq.com/overview`
- The specific scenario URL most relevant to their environment
- The security URL if procurement was on the call
- A specific proposed next step with a date

---

## Things to avoid in the call

- Do not pitch AI features.
- Do not pitch open source or self-hosted as a differentiator.
- Do not lead with pricing.
- Do not chest-thump on competitors. Speak about categories, not vendors.
- Do not over-claim certifications. "Mapped" is not "certified." Be precise.
- Do not promise customer-managed keys, multi-region per tenant, or features not on the public product/site today.
- Do not improvise legal commitments. Route to security@.
- Do not run over 30 minutes without the buyer asking.

---

## Recommended next follow-up asset after the demo

A short **environment-specific recovery brief** generated for the prospect after the call. One page. Three sections:

1. Their tenant context as you understood it (workloads, users, regulated requirements).
2. The two or three KavachIQ capabilities most relevant to that context, with a sentence each.
3. A proposed concrete next step (technical walkthrough, security review, scenario walkthrough).

Send as a follow-up email body with `https://kavachiq.com/overview` linked at the bottom for forwarding. No PDF needed unless procurement requests one. If they do, "Save as PDF" from `/overview` produces the artifact.

---

*This script reflects the public site at the time of writing. If a section, scenario, or page changes, update the references here so the live demo and the script stay in sync.*
