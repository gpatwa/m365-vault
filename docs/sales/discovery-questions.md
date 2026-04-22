# Discovery Question Bank — KavachIQ for Microsoft 365

**Audience**: Founder-led and technical sellers. First discovery calls, first demos, follow-up technical calls.
**Format**: Pick-list, not a script. Choose the 3–5 most relevant questions for the buyer in front of you.
**Use case**: Companion to `founder-demo-script.md` (which carries a tight default discovery section) and `recovery-brief-template.md` (which the answers feed directly into).

> Strategic anchor: KavachIQ is the **identity-first cyber recovery platform for Microsoft Entra and Microsoft 365**. Every question below is designed to surface recovery-workflow signals, not generic backup needs.

---

## How to use this bank

1. Before the call, **scan the categories** and pick 3–5 questions that match the buyer's role and the call type. Mark them in your prep notes.
2. **Open with one operational question**, not a meta one. "How does your team handle X" lands; "what are your priorities" does not.
3. **Listen more than you ask.** Most early calls reveal more in the silence after a good question than in the next question.
4. **Take notes that feed the recovery brief.** Each category below maps to a section of `recovery-brief-template.md`, so good notes make the follow-up brief almost write itself.
5. If a question lands hard, **stay there.** Drop the rest of the list and dig into what the buyer is actually saying.

---

## 1. Environment and tenant shape

Map for: recovery brief Section 1 (Your environment, as we understood it).

- Roughly how many Entra users, mailboxes, SharePoint sites, and OneDrive accounts are in scope?
- Single tenant, multi-geo, or part of an MSP relationship?
- Which Microsoft 365 workloads matter most for recovery in your environment: Entra, Exchange, OneDrive, SharePoint, Teams?
- Any regulated or sensitive workloads in M365 — for example, legal hold, retention labels, eDiscovery cases, ePHI, or financial records?
- Microsoft 365 SKU mix — E3, E5, E5 with security/compliance add-ons?
- Anything unusual about your tenant configuration we should know about up front (multi-tenant federation, hybrid identity, complex administrative units)?

---

## 2. Identity and admin exposure

Map for: recovery brief Section 3 (Likely recovery gaps).

- How many Global Admins are in your tenant today, and how do you control that number?
- What does your privileged role assignment process look like — standing access, just-in-time, or both?
- Are conditional access policies version-controlled or change-managed in any way?
- How do you currently track changes to OAuth grants and service principals?
- Have you ever had to revert a conditional access policy, MFA enforcement, or role change after the fact? How did that go?
- If a privileged identity was compromised right now, what is the first thing your team would do?
- How does your team monitor for unusual identity activity in Entra today?

---

## 3. Backup, retention, and recovery posture

Map for: recovery brief Section 1 (current tooling) and Section 3 (gaps).

- What backup or recovery tooling do you have today for Microsoft 365: native retention only, third-party backup vendor, in-house scripts, or a combination?
- If you have third-party backup, which workloads are covered, and how often is recovery actually tested?
- How does your team think about retention versus recovery — are those treated as the same thing or different?
- If 1,000 mailboxes were deleted right now, how would you recover, and how confident are you in the order?
- Are mailboxes ever purged past Microsoft's 30-day soft-delete window in your environment, intentionally or by accident?
- Have you tried to recover content past native recycle-bin or retention windows? What happened?
- How does your team verify a recovery is actually complete, beyond "the script finished"?

---

## 4. Incident history and trigger event

Map for: recovery brief Section 2 (the recovery concern in scope).

- Has your team handled a Microsoft 365 incident in the last 12 to 24 months that involved identity, mass deletion, or retention drift? What did the recovery look like?
- Anything specific prompting this conversation now: a recent incident, an audit finding, a vendor renewal, a new compliance requirement, a board ask?
- If you had to point to the recovery scenario most likely to hit your tenant in the next year, what would it be?
- Are there incidents you have read about in your sector recently that changed how you think about M365 recovery?
- How are recovery exercises (tabletop, full restore tests) handled in your team today?

---

## 5. Operational recovery process

Map for: recovery brief Section 4 (where KavachIQ fits) and the founder demo script's scenario walk.

- Walk me through your recovery runbook for a privileged-identity compromise in Entra. Is one written down? When was it last reviewed?
- Who decides the order of restore in an incident — IT, security, business leadership? How is that decision made under pressure?
- How do you communicate to the business during a recovery — what is the artifact you give leadership?
- How do you produce evidence for legal, compliance, or audit after a recovery?
- If part of an Entra change had to be reverted but other parts kept, how would you handle that today?
- Where does your team feel most exposed in the gap between "we have a backup" and "we are actually back online"?

---

## 6. Security and procurement readiness

Map for: recovery brief Sections 5 and 6, and `objection-handling.md` Objection 5.

- Who in your organization runs vendor-risk and security review? How does that process typically run?
- What review artifacts will your team need to evaluate KavachIQ — SOC 2 mapping, BAA, DPA, vendor-risk questionnaire?
- Are there specific frameworks your security team maps controls to: SOC 2, HIPAA, GDPR, DORA, FINRA, internal IT general controls?
- Any specific data residency, region, or sovereignty requirements we should be aware of?
- Does your team have constraints on third-party access to your Microsoft 365 tenant that we should plan around?

---

## 7. Stakeholders and buying process

Map for: recovery brief Section 6 (next step) and the founder demo script's close.

- Who owns Microsoft 365 recovery in your organization day to day — IT, security, both?
- Who would be in the room for a follow-up technical evaluation?
- Who is the economic decision-maker for a tool in this category?
- What does evaluation typically look like in your team — POC, paper review, both?
- Are there budget cycles or fiscal-year boundaries that shape the timing of this decision?
- If the recovery story we are walking today resonates, what is the natural next step inside your team?

---

## 8. Vertical-specific questions

Pick from the relevant vertical only. Skip if not applicable.

### Healthcare

- How does your team think about ePHI recovery specifically — same workflow as the rest of the tenant, or special handling?
- Where does your last HIPAA audit or risk assessment land on Microsoft 365 backup or recovery?
- Are clinical user mailboxes (CMIO, on-call clinicians, privacy officer) prioritized in your recovery thinking today?
- What is your BAA process for new vendors that touch ePHI in M365?

### Financial services

- Under SOX, FINRA, or DORA, where does Microsoft 365 recovery sit in your control framework today?
- Does your audit process require evidence of recovery, beyond evidence of backup?
- Are records-bearing workloads (Exchange, SharePoint sites with regulated content) treated differently from general M365 in your recovery posture?
- For DORA-regulated entities: how are you sizing operational resilience testing for M365 specifically?

### Legal

- How does your firm handle litigation hold and matter-specific retention in M365 today?
- If a privileged attorney mailbox was purged or compromised, what is your recovery and chain-of-custody process?
- Are case workspaces in SharePoint protected differently from general firm content?
- What does your ethics counsel or risk partner expect from a vendor that touches privileged client data?

---

## 9. Next-step qualification

Map for: recovery brief Section 6 and the founder demo script's close.

- Based on what we walked today, what feels most relevant to your environment?
- Who else inside your team should see this? Should I send the overview link or a specific scenario?
- Would a 60-minute deeper walkthrough with your security or admin team be a useful next step? When would work?
- If a 30-day evaluation made sense, what would your team need to see signed off before starting?
- Anything I have not covered today that is going to come up in your internal conversation about this?

---

## The best 5 questions for a first call

If you only have time to ask five, and you do not yet know the buyer well, pick from this set. They are sequenced.

1. **Trigger**: "Anything specific prompting this conversation now — a recent incident, an audit finding, a vendor renewal, or a new compliance requirement?"
2. **Environment shape**: "Roughly how many Entra users and which Microsoft 365 workloads are in scope for recovery in your environment?"
3. **Recovery posture**: "If 1,000 mailboxes were deleted right now, how would you recover, and how confident are you in the order?"
4. **Identity exposure**: "If a Global Admin in your tenant was compromised today, what is the first thing your team would do?"
5. **Stakeholders**: "Who owns Microsoft 365 recovery day to day, and who would be in the room for a follow-up?"

These five answer the questions every recovery brief needs to fill, and they surface the buyer's actual recovery story in under ten minutes.

---

## Don't interrogate the buyer

A discovery call is not a survey. Avoid:

- **Reading questions in order.** Pick three to five. Make them feel like a conversation, not a checklist.
- **Asking everything in one breath.** Space questions across the call so the buyer keeps talking.
- **Asking questions whose answer is on their LinkedIn / company website / public docs.** Do that homework before the call.
- **Asking compliance or procurement questions before establishing operational pain.** Those questions land harder once you have already framed the recovery problem.
- **Yes/no questions.** "Do you have backup?" is dead. "How does your team handle recovery when X happens?" opens the conversation.
- **Hypotheticals when a real incident is on the table.** If they have just told you about a real event, dig into that. Don't pivot to a generic scenario.

If the buyer is opening up, **stop asking questions and let them talk.** The most useful discovery moments come from listening, not from running through the bank.

---

## Adapting by buyer type

| Buyer | Lean on these categories | Skip or de-prioritize |
|---|---|---|
| **M365 admin / Entra admin** | Environment, Identity exposure, Operational recovery process | Buying process, vendor-risk specifics |
| **IT or security leader (CISO, CIO, IT Director)** | Recovery posture, Identity exposure, Incident history, Stakeholders | Deep technical-restore minutiae |
| **Procurement / risk reviewer** | Security and procurement readiness, Stakeholders, Next-step qualification | Operational recovery walk-through (route them to the relevant scenario instead) |
| **Champion who needs to brief their CISO/CIO** | Stakeholders, Next-step qualification, vertical questions | Deep questions on identity exposure they don't own |

---

## How this bank fits the rest of the sales asset set

- **`founder-demo-script.md`** has a tight, default discovery section (~10 questions) for a 30-minute first call. **Use that** if you have not had time to prep. Use **this bank** when you have time to pick.
- **`recovery-brief-template.md`** is the post-call follow-up artifact. The categories here are deliberately mapped to its sections, so good answers in the call become a quick brief afterward.
- **`objection-handling.md`** is for live responses to objections that surface during or after discovery. The two assets are complementary: discovery surfaces the operational story; objection handling reframes when the buyer pushes back.
- **Vertical one-pagers** (`healthcare-one-pager.md`, `finance-one-pager.md`, `legal-one-pager.md`) are forwardable leave-behinds when the vertical-specific section here lands.

---

*Keep the bank in sync with the public site and the rest of `docs/sales/`. If a category, scenario, or capability shifts on `/welcome`, `/scenarios/*`, `/security`, or `/overview`, update the questions here so live discovery and the recovery brief stay aligned.*
