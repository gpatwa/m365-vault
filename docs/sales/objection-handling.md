# Objection Handling — KavachIQ for Microsoft 365

**Audience**: Founder-led and technical sellers. Demos, follow-ups, early sales conversations.
**Format**: Quick-reference sheet. Skim before a call, glance at it during one.
**Use case**: A response pattern to lean on, not a script to read aloud.

> Strategic anchor: KavachIQ is the **identity-first cyber recovery platform for Microsoft Entra and Microsoft 365**. Every objection answer below positions on that. Do not slip back into "yet another M365 backup" framing.

---

## How to use this sheet

1. Read the **good answer** in your own voice. Do not recite it.
2. Always **acknowledge the buyer's point first**, then reframe to recovery workflow / identity-first / blast radius / verification.
3. Resist the urge to win the sentence. Win the next 20 minutes by handing back the conversation cleanly.
4. **Send the proof asset** the same day — link in the follow-up email or in the chat during the call.
5. If you do not know the answer, say so and route to `security@kavachiq.com` or commit to a follow-up. Never improvise features, certifications, or commitments.

---

## Objection 1 — "Why not just use Microsoft's native tools?"

**What the buyer really means**: We already pay Microsoft. Justify the spend on top.

**Good answer**:
> Microsoft 365 retention, Purview, and the new Entra Backup capability are real, and they keep getting better. They preserve copies of mailboxes, sites, and identity configuration. KavachIQ runs the operational recovery layer on top: blast radius across identity and data, identity-first restore order, and recovery verification with evidence. The two are complementary. We don't replace Microsoft's tooling — we run the recovery on top of it.

**Proof to send next**: `https://kavachiq.com/welcome` (the "Why backup alone is not enough" section) · `https://kavachiq.com/scenarios/compromised-global-admin`

---

## Objection 2 — "How are you different from Veeam / Rubrik / Druva?"

**What the buyer really means**: I'm trying to slot you into a category I already understand.

**Good answer**:
> Veeam, Rubrik, and Druva preserve Microsoft 365 data well. We are not trying to replace them. KavachIQ focuses on the operational recovery problem on top: identity-first sequencing, blast radius across identity and data, criticality-based restore order, and recovery verification. If you already have a backup vendor, KavachIQ sits alongside them on the recovery side. If you don't, we cover both for the Microsoft 365 stack.

**Avoid**: naming and trashing specific competitors. Speak about categories — native tools, generic backup, manual restore, broad cyber suites.

**Proof to send next**: `https://kavachiq.com/welcome` (the "Why KavachIQ" category comparison) · `https://kavachiq.com/overview`

---

## Objection 3 — "Why identity-first recovery? Isn't data the priority?"

**What the buyer really means**: Convince me the category itself is real.

**Good answer**:
> Most Microsoft 365 incidents that escalate are mixed events. A privileged identity is compromised. Conditional access is loosened. OAuth grants are added. *Then* the data side starts drifting. By the time someone notices a missing mailbox, the control plane is already in a different state. Restoring patient data, case files, or financial records into a tenant whose admin role assignments are still wrong puts the data right back into a compromised context. Identity-first recovery means we restore the control plane before the data plane. Data recovery without identity recovery is incomplete.

**Proof to send next**: `https://kavachiq.com/welcome` (the "Why identity-first matters" section) · `https://kavachiq.com/scenarios/compromised-global-admin`

---

## Objection 4 — "Are you a backup product or something else?"

**What the buyer really means**: Help me categorize you for my budget line / procurement codes.

**Good answer**:
> We are a cyber recovery platform for Microsoft 365 and Entra. Backup vendors preserve data. KavachIQ runs the recovery workflow on top: identity-first restore order, blast radius assessment, criticality-based prioritization, and recovery verification with evidence. Some prospects classify us as cyber recovery, some under data protection. Recovery is the more accurate primary lens. Either category code works for procurement, and we can support whichever lines up with your existing vendor taxonomy.

**Proof to send next**: `https://kavachiq.com/overview` · `https://kavachiq.com/welcome`

---

## Objection 5 — "How do you handle security and procurement review?"

**What the buyer really means**: My CISO and procurement team will need to review you. Tell me the path so I can plan internally.

**Good answer**:
> Our public security page covers principles, controls, the full tenant data handling lifecycle, the procurement FAQ, and the architecture. Formal artifacts — SOC 2 mapping, BAA, DPA, vendor-risk questionnaire responses — route through `security@kavachiq.com`. Typical reply within one business day. We can also run a parallel security and procurement review track alongside any technical evaluation, so neither side blocks the other.

**Avoid**: claiming a certification we don't have. We have **mapped** controls. The SOC 2 report itself routes through `security@`.

**Proof to send next**: `https://kavachiq.com/security` · email path: `security@kavachiq.com`

---

## Objection 6 — "What is the right first use case for us?"

**What the buyer really means**: Help me size where to start without committing the whole org.

**Good answer**:
> The strongest first use case for most teams is the compromised Global Admin scenario. It is the one that exposes the recovery-order problem most cleanly, regardless of vertical. If your team has a more specific concern — bulk mailbox loss with retention drift, destructive SharePoint and OneDrive deletion — we'll center the walkthrough on that instead. We have concrete narratives for all three. The first call is 30 minutes, scoped to one scenario in your environment.

**Proof to send next**: `https://kavachiq.com/scenarios` · the scenario closest to their situation

---

## Objection 7 — "How should we think about rollout or evaluation?"

**What the buyer really means**: I need a realistic POC / eval shape before I commit time.

**Good answer**:
> Recommend starting with a focused walkthrough — 30 to 60 minutes — on one real recovery scenario in your environment. After that, run a procurement and security review track in parallel through `security@`. Production rollout uses Microsoft Entra OAuth admin consent, so technical onboarding is fast; the deployment timeline usually depends more on your internal change-management process than on KavachIQ. We can phase by workload (Entra first, then Exchange, then SharePoint and OneDrive) if that suits your governance model.

**Proof to send next**: `https://kavachiq.com/contact` · the founder demo script (`docs/sales/founder-demo-script.md`) for internal seller alignment

---

## Objection 8 — "Why do we need this if we already have retention / backup / versioning?"

**What the buyer really means**: Prove the gap on top of what I already have. Or I won't fund this.

**Good answer**:
> Retention, backup, and versioning all preserve data well. None of them sequence a recovery, compute blast radius across identity and data, or verify the recovery is complete with evidence. The questions that matter during an actual incident are operational: what changed, who is affected, what to restore first, and how do we know we are back online. If your team's recovery story today ends at "we have a backup," the gap is everything that comes after that.

**Proof to send next**: `https://kavachiq.com/welcome` (the "Why backup alone is not enough" section) · `https://kavachiq.com/scenarios/bulk-mailbox-deletion-retention-drift`

---

## What not to say

- **"Microsoft doesn't back up your data"** or any anti-Microsoft hero framing. Off-strategy on the public site, off-strategy in calls.
- **"Veeam/Rubrik/Druva can't do this"** with no qualification. Speak about categories, not chest-thumping. The buyer almost certainly already has a vendor relationship somewhere.
- **"AI-powered" anything**. We are not pitching AI features.
- **"Open source"** or **"self-hosted"** as a differentiator. Not the GTM.
- **"Free for 25 users"**, **"$1.50/user"**, or any pricing anchor. Pricing belongs in a separate scoped conversation.
- **"SOC 2 certified"**, **"HIPAA certified"**, **"DORA certified"**. We have mapped controls. Formal certification language is a real over-claim — and the kind of thing your buyer's CISO will catch.
- **"We support customer-managed keys"** or **"multi-region per tenant"** unless those become real, public product features. They are not today.
- **"It deploys in 10 minutes"**. Onboarding is OAuth-driven and fast, but enterprise change management isn't 10 minutes. Don't anchor naive timelines.
- **Improvised answers about features that don't exist**. Say "I don't know, let me confirm and follow up" and route to `security@` or `hello@`.

---

## Adapting answers by buyer type

| Buyer | Lean on | Avoid |
|---|---|---|
| **M365 admin / Entra admin** | Operational recovery flow, Entra-specific examples, restore-order under pressure, time-to-recover questions | Compliance-heavy framing if they did not raise it |
| **IT / security leader (CISO, CIO, IT Director)** | Identity-first sequencing, recovery confidence with evidence, NIST SP 800-184 alignment, blast radius | Deep technical-restore minutiae unless asked |
| **Procurement / risk reviewer** | `/security` content, mapped controls, `security@` routing, BAA / DPA / SOC 2 mapping availability | Live product demos that require technical context they don't have |
| **CISO specifically** | Control plane integrity during recovery, audit defensibility, evidence artifacts that survive an incident review | Generic "recovery" pitch — make it about the gap their existing tooling leaves |

---

## Quick proof-asset map

| Objection | Primary proof | Secondary proof |
|---|---|---|
| Why not native tools? | `/welcome` "Why backup alone is not enough" | `/scenarios/compromised-global-admin` |
| Vs. Veeam/Rubrik/Druva? | `/welcome` category comparison | `/overview` |
| Why identity-first? | `/welcome` "Why identity-first matters" | `/scenarios/compromised-global-admin` |
| Backup product or something else? | `/overview` | `/welcome` |
| Security and procurement review? | `/security` | `security@kavachiq.com` |
| Right first use case? | `/scenarios` | The closest scenario page |
| Rollout / evaluation? | `/contact` | `docs/sales/founder-demo-script.md` |
| We already have retention/backup? | `/welcome` "Why backup alone is not enough" | `/scenarios/bulk-mailbox-deletion-retention-drift` |

---

*Keep this sheet in sync with the public site. If a section, scenario URL, or capability name changes on `/welcome`, `/scenarios/*`, `/security`, or `/overview`, update the references here so the live conversation and the sheet do not drift apart.*
