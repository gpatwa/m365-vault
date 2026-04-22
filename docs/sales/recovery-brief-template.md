# Recovery Brief Template — KavachIQ for Microsoft 365

**Audience**: Internal sales / founder use. Fill after a first or second demo. Send to the prospect as a forwardable follow-up.
**Time to fill**: 10–15 minutes.
**Length goal**: One short page when filled. Resist expansion.

> Strategic anchor: KavachIQ is the **identity-first cyber recovery platform for Microsoft Entra and Microsoft 365**. Keep this in mind for every section. Do not turn the brief into a generic backup pitch.

---

## How to use this template

1. **Duplicate this file**, do not edit it in place. Save the copy as `recovery-brief-{ACCOUNT_SLUG}-{YYYY-MM-DD}.md` in your local working folder, or paste sections directly into the follow-up email.
2. **Fill from your call notes only**. If you do not know an answer, leave the placeholder with `[unknown — confirm]`. Do not invent.
3. **Stay on what is supported by the current site/product**. Reference the public assets at the bottom rather than restating their content.
4. **Send within 24 hours** of the call. Speed matters more than polish.
5. **Forwardable by default**. Assume the recipient will share it with their CISO, CIO, or procurement lead. Write so it stands alone.
6. **Send by email body or markdown attachment**. PDF only on request — point them at `https://kavachiq.com/overview` for that.

---

## ✂ — TEMPLATE STARTS BELOW. COPY FROM HERE. — ✂

# Recovery brief for {{ACCOUNT_NAME}}

*Prepared by {{YOUR_NAME}}, KavachIQ · {{DATE}}*

This brief summarizes how KavachIQ for Microsoft 365 fits {{ACCOUNT_NAME}}'s environment and recovery posture, based on our conversation on {{CALL_DATE}}. It is intended to be forwardable inside your team. Anything that needs deeper review can be routed through the contacts at the bottom.

---

## 1. Your environment, as we understood it

- **Microsoft 365 footprint**: {{e.g., ~1,200 users, single tenant, US East, multi-geo: no}}
- **Workloads in scope for recovery**: {{e.g., Microsoft Entra, Exchange Online, OneDrive, SharePoint, Teams — all five}}
- **Regulated or compliance context**: {{e.g., HIPAA, SOC 2, GDPR, DORA, internal IT general controls — or "none specifically named"}}
- **Backup or recovery tooling today**: {{e.g., native M365 retention only · third-party backup vendor · in-house PowerShell scripts · combination}}
- **Recent recovery work or incidents discussed**: {{e.g., recent privileged-account compromise · planned offboarding cleanup · audit finding · or "none discussed"}}
- **Stakeholders likely involved in evaluation**: {{e.g., M365 admin (lead), IT director, CISO, procurement lead}}

---

## 2. The recovery concern in scope

In our conversation, the recovery problem most relevant to {{ACCOUNT_NAME}} is:

> {{One or two sentences naming the incident type or recovery gap. Examples:
> "Recovering safely from a compromised Global Admin without restoring data into a tenant whose control plane is still unsafe."
> "Bringing back mailboxes after a bulk deletion event when some are already past Microsoft's 30-day soft-delete window."
> "Producing defensible evidence of recovery for a compliance review after destructive change in SharePoint."}}

If your priorities have shifted since we spoke, let us know — the rest of this brief adapts to the scenario you actually want to walk.

---

## 3. Likely recovery gaps in this environment

Based on what we discussed, these are the operational gaps most likely to surface during a real incident. Each is something KavachIQ is built to address:

- **{{Gap 1 — e.g., Identity rollback}}**: {{One sentence on what is not supported well by current tooling for this account. Avoid criticizing specific vendors. Example: "Reverting Entra conditional access, OAuth grants, and privileged role changes after a compromise is hard to do in the right order with native tools."}}
- **{{Gap 2 — e.g., Blast radius visibility}}**: {{e.g., "When a deletion event hits multiple users and sites, getting a coordinated picture of who and what is affected is mostly manual today."}}
- **{{Gap 3 — e.g., Recovery beyond native windows}}**: {{e.g., "Mailboxes past the 30-day soft-delete window or SharePoint content past recycle-bin retention is not recoverable through Microsoft 365 alone."}}
- **{{Gap 4 — optional, e.g., Recovery verification evidence}}**: {{e.g., "There is no clear, defensible artifact today to show compliance that a recovery is actually complete."}}

Use 2–4 gaps. If none of these match the call, reframe to what was actually discussed. Do not pad.

---

## 4. Where KavachIQ fits for {{ACCOUNT_NAME}}

KavachIQ runs an identity-first cyber recovery workflow on top of your Microsoft 365 environment. For your context, the parts that matter most are:

- **{{Capability 1 — pick from the 6 product pillars based on the gap above}}**: {{One sentence relevant to the account. Example: "Entra Recovery — snapshot and restore the 12 Entra ID object types, including conditional access policies, OAuth grants, service principals, and role assignments, so identity controls come back before data."}}
- **{{Capability 2}}**: {{e.g., "Blast Radius Analysis — diff identity and data state across snapshots so you can see exactly who and what is affected, not estimate it."}}
- **{{Capability 3}}**: {{e.g., "Guided Recovery Plans — pre-computed, NIST SP 800-184-aligned plans refreshed on a schedule. Identity first, critical users next, business data after."}}

Reference, do not copy: the full set of capabilities is at <https://kavachiq.com/welcome> under "Purpose-built for Microsoft 365 recovery."

---

## 5. Relevant proof to walk next

These public assets cover the proof points most relevant to your environment. They are forwardable.

- **Closest scenario to your incident type**: <{{ONE_SCENARIO_URL}}>
  - <https://kavachiq.com/scenarios/compromised-global-admin> — privileged identity compromise
  - <https://kavachiq.com/scenarios/destructive-sharepoint-onedrive-deletion> — destructive deletion across SharePoint and OneDrive
  - <https://kavachiq.com/scenarios/bulk-mailbox-deletion-retention-drift> — bulk mailbox deletion and retention drift
- **Live product walkthrough**: <https://kavachiq.com/tour>
- **Security and trust controls** (for your security or procurement reviewer): <https://kavachiq.com/security>
- **One-page overview** (forwardable, "Save as PDF" works for procurement files): <https://kavachiq.com/overview>

---

## 6. Recommended next step

Pick **one** concrete next step. Be specific about who, what, when.

> {{One of:
> "A 60-minute technical walkthrough with {{ADMIN_NAME}} and {{SECURITY_LEAD_NAME}}, focused on {{SCENARIO_NAME}} in your environment. Proposed: {{DATE/TIME WINDOW}}."
> "A security and procurement review session with your team. We can route SOC 2 mapping, DPA, and questionnaire responses through security@kavachiq.com beforehand if helpful."
> "A scenario deep-dive on {{SCENARIO_NAME}} with {{INCIDENT_RESPONSE_LEAD}} in the room. Proposed: {{DATE/TIME WINDOW}}."
> "A short follow-up call with {{ECONOMIC_BUYER_NAME}} to align on scope and decision process. Proposed: {{DATE/TIME WINDOW}}."}}

If a different next step makes more sense given internal cycles at {{ACCOUNT_NAME}}, just reply and we will adjust.

---

## Contacts

- **General / sales**: hello@kavachiq.com
- **Security and procurement**: security@kavachiq.com
- **Direct**: {{YOUR_NAME}} · {{YOUR_EMAIL}} · {{OPTIONAL_PHONE}}

---

*This brief is based on a working conversation, not an audit or formal proposal. Anything that needs to be a formal artifact (SOC 2 report, DPA, vendor-risk questionnaire) routes through security@kavachiq.com.*

## ✂ — TEMPLATE ENDS ABOVE. STOP COPYING HERE. — ✂

---

## Internal notes for the seller

These are not for the prospect. Keep them in your working copy or delete before sending.

### Things to never include
- **Pricing**. Pricing belongs in a separate conversation aligned to the actual deployment scope. Do not anchor or improvise tiers in the brief.
- **Customer-managed keys, multi-region per tenant, self-hosted, or open-source claims** — none of these are public-facing commitments today.
- **Specific recovery time numbers** ("under 30 minutes") unless you can actually defend them for the prospect's environment.
- **"AI-powered" or "Smart Engine" framing** — off-strategy on public surfaces and on this brief.
- **Anti-Microsoft hero framing** ("Microsoft doesn't back up your data"). Acknowledge native tools exist; position KavachIQ on top of them.
- **Comparisons to specific named competitors**. Speak about categories (native tools / generic backup / manual restore / broad cyber suites).

### Picking the right scenario URL
- **Privileged identity compromise** → `compromised-global-admin`
- **Mass deletion across sites/files** → `destructive-sharepoint-onedrive-deletion`
- **Mailbox-heavy or retention-policy issue** → `bulk-mailbox-deletion-retention-drift`
- If they care about more than one, link the index: `https://kavachiq.com/scenarios`

### Picking the next step
| Buyer signal | Next step |
|---|---|
| Asked about specific incident in their tenant | Scenario deep-dive with their IR lead |
| Asked about SOC 2 / DPA / questionnaires | Security & procurement review, route security@ in parallel |
| Champion is technical, decision-makers absent | Multi-stakeholder follow-up with named attendees |
| Buyer is the decision-maker, technical buy-in needed | Technical walkthrough with their admins in the room |

### Sending checklist
- [ ] All `{{...}}` placeholders filled or explicitly marked `[unknown — confirm]`
- [ ] Exactly one next step, with proposed time window
- [ ] Direct contacts at the bottom
- [ ] Sent within 24 hours of the call
- [ ] Logged in CRM with the URLs you sent

---

## Worked example (for reference, do not send to a prospect)

This shows what a filled brief should feel like. It is illustrative, not a real account.

> # Recovery brief for Acme Health Group
>
> *Prepared by Sam Patel, KavachIQ · 21 April 2026*
>
> ## 1. Your environment, as we understood it
> - **Microsoft 365 footprint**: ~700 users, single tenant, US-East
> - **Workloads in scope for recovery**: Entra ID, Exchange, SharePoint, Teams (OneDrive in scope but lower priority)
> - **Regulated or compliance context**: HIPAA-covered entity; SOC 2 Type II in progress
> - **Backup or recovery tooling today**: Native M365 retention only; some PowerShell scripts for offboarding
> - **Recent recovery work**: Mailbox cleanup script over-deleted ~80 mailboxes last quarter; manual recovery took 5 days
> - **Stakeholders**: Maria Chen (M365 admin, lead), David Lee (IT director), Priya Rao (CISO)
>
> ## 2. The recovery concern in scope
> > Bringing back mailboxes after a bulk deletion event when some are already past Microsoft's 30-day soft-delete window, with audit-friendly evidence for the next HIPAA review.
>
> ## 3. Likely recovery gaps in this environment
> - **Recovery beyond native windows**: Mailboxes past 30-day soft-delete are not recoverable via M365 alone, which is exactly what triggered the prior 5-day recovery.
> - **Coordinated restore order**: With a script-driven incident, prioritizing executives and compliance officers ahead of broader restore is hard to do manually under pressure.
> - **Recovery verification evidence**: For HIPAA audit, you need a defensible artifact that the recovery is complete and that retention/holds are back in the correct state.
>
> ## 4. Where KavachIQ fits for Acme Health Group
> - **M365 Data Recovery**: unlimited point-in-time restore for Exchange, including mailboxes past the native window.
> - **Criticality-Based Recovery**: scores users so executives and compliance leads come back first, automatically.
> - **Recovery Verification**: checksum, sign-in, and policy-active checks; produces a recovery report aligned to the kind of evidence HIPAA reviewers expect.
>
> ## 5. Relevant proof to walk next
> - Closest scenario: <https://kavachiq.com/scenarios/bulk-mailbox-deletion-retention-drift>
> - Live product walkthrough: <https://kavachiq.com/tour>
> - Security and trust: <https://kavachiq.com/security>
> - One-page overview: <https://kavachiq.com/overview>
>
> ## 6. Recommended next step
> > A 60-minute technical walkthrough with Maria, David, and Priya focused on the bulk-mailbox-deletion scenario in your environment. Proposed: week of 28 April, Tuesday or Wednesday afternoon ET.
>
> ## Contacts
> - General: hello@kavachiq.com
> - Security and procurement: security@kavachiq.com
> - Direct: Sam Patel · sam@kavachiq.com

---

*Keep this template in sync with the public site. If a scenario URL, capability name, or contact path changes on `/welcome`, `/scenarios/*`, `/security`, or `/overview`, update the references here.*
