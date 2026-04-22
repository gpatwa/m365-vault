# Follow-Up Email Templates — KavachIQ for Microsoft 365

**Audience**: Founder-led and technical sellers. Post-call follow-up after intro/discovery, demo/walkthrough, and security/procurement review.
**Format**: Three short reusable templates. Personalize in 2–5 minutes per send.
**Use case**: Companion to `recovery-brief-template.md` (the structured artifact for serious follow-up) and `outreach-templates.md` (which handles cold first contact).

> Strategic anchor: KavachIQ is the **identity-first cyber recovery platform for Microsoft Entra and Microsoft 365**. Every email below positions on that. Do not slip back into generic backup or PLG-style nurture language.

---

## How to use these templates

1. **Send within 24 hours** of the call. Speed matters more than polish in early sales.
2. **Reference something specific** the buyer said. The opener should sound like a thoughtful human follow-up, not a CRM macro.
3. **One concrete next-step ask per email.** Not three. Pick the highest-probability one.
4. **Keep the body skimmable.** A buyer reads on their phone. If it does not fit on one screen, it is too long.
5. **Forwardable by default.** Assume the recipient will share with their CISO, CIO, or procurement lead. Avoid private-context language.
6. **Pair with `/overview`** as the forwardable one-pager when the buyer needs to brief someone internally.

---

## Template 1 — After a first intro or discovery call

### Subject line options
- Recap from our call · {{ACCOUNT_NAME}} on Microsoft 365 recovery
- Following up — KavachIQ for {{ACCOUNT_NAME}}
- {{BUYER_FIRST_NAME}}, recap and next steps after today

### Body

> Hi {{BUYER_FIRST_NAME}},
>
> Thanks for the time today. The piece that stood out for me was {{ONE_SPECIFIC_THING_THEY_SAID — e.g., "the script-driven mailbox cleanup last quarter that took five days to recover from", or "the gap you mentioned between Entra config changes and your team's ability to revert them safely"}}. That is exactly the operational recovery problem KavachIQ is built around.
>
> A short recap of what we covered:
>
> - **Your environment**: {{e.g., ~700 M365 users, single tenant, regulated under HIPAA}}
> - **The recovery concern**: {{One sentence on what matters most to them — e.g., "recovering mailboxes past the native window with audit-defensible evidence"}}
> - **Where KavachIQ likely fits**: identity-first restore order, blast radius across identity and data, and recovery verification with evidence
>
> Two things you can read or forward:
>
> - The closest scenario to your situation: <{{ONE_SCENARIO_URL — pick one based on their concern}}>
> - A one-page overview, forwardable inside your team: <https://kavachiq.com/overview>
>
> Concrete next step I would suggest: a 60-minute technical walkthrough with {{ADMIN_NAME_OR_ROLE}} and {{SECURITY_LEAD_NAME_OR_ROLE}} in the room, focused on {{SCENARIO_NAME}} in your environment. I have time {{DAY_OR_DATE_RANGE}}. Does any of that work?
>
> If a different shape makes more sense given your internal cycles, just let me know.
>
> Best,
> {{YOUR_NAME}}
> KavachIQ · hello@kavachiq.com

### Pairs with
- `/scenarios/*` — pick the scenario URL that matches what the buyer raised in discovery
- `/overview` — the forwardable one-page asset
- `recovery-brief-template.md` — if the call gave you enough to write a real brief, send the brief in addition to (or instead of) this email

---

## Template 2 — After a technical walkthrough or demo

### Subject line options
- Walkthrough recap and next steps · KavachIQ for {{ACCOUNT_NAME}}
- After today's recovery walkthrough — {{ACCOUNT_NAME}}
- {{BUYER_FIRST_NAME}}, recap from the technical session

### Body

> Hi {{BUYER_FIRST_NAME}},
>
> Thanks to you and {{OTHER_ATTENDEE_NAMES}} for the time today. The walkthrough through {{SCENARIO_NAME — e.g., "the compromised Global Admin scenario"}} was the right call given {{REASON_TIED_TO_THEIR_ENVIRONMENT — e.g., "your concerns about how quickly conditional access drift could expand blast radius in your tenant"}}.
>
> A few of the points we covered that seemed to land:
>
> - {{POINT_1 — e.g., "the identity-first restore order: Entra controls before mailbox content, with critical users prioritized"}}
> - {{POINT_2 — e.g., "blast radius computed as a diff against the last known-good snapshot, rather than estimated under pressure"}}
> - {{POINT_3 — e.g., "the recovery verification artifact your team would have for HIPAA review after an incident"}}
>
> Open items I owe you:
>
> - {{OPEN_ITEM_1 — e.g., "Routing your DPA request through security@kavachiq.com — done; expect a reply within one business day"}}
> - {{OPEN_ITEM_2 — e.g., "Sending the {{SCENARIO_NAME}} scenario page for {{NAMED_STAKEHOLDER}}"}}
>
> Useful to share internally:
>
> - The scenario we walked: <{{SCENARIO_URL}}>
> - Security and trust controls (for your security or procurement reviewer): <https://kavachiq.com/security>
> - One-page overview, forwardable: <https://kavachiq.com/overview>
>
> Concrete next step: {{ONE_OF — "a 30-minute alignment call with {{ECONOMIC_BUYER_NAME}} to confirm scope and decision process" / "a security and procurement review session with your team — I can route the SOC 2 mapping and DPA through security@kavachiq.com beforehand" / "a focused walkthrough on a second scenario relevant to {{TEAM}}"}}. Proposed: {{DATE_RANGE}}.
>
> Anything I should adjust before sending this around your team?
>
> Best,
> {{YOUR_NAME}}

### Pairs with
- `recovery-brief-template.md` — fill and attach (or paste) the recovery brief alongside this email when the walkthrough went well
- `/security` — when the buyer raised compliance, controls, or vendor-risk questions during the walkthrough
- A second scenario URL — when the buyer mentioned an incident pattern different from the one you walked

---

## Template 3 — After a security or procurement review

### Subject line options
- Security review recap and next steps · KavachIQ for {{ACCOUNT_NAME}}
- Following up on the security review — {{ACCOUNT_NAME}}
- Next steps after today's security and procurement session

### Body

> Hi {{BUYER_FIRST_NAME}},
>
> Thanks to you and {{SECURITY_AND_PROCUREMENT_ATTENDEE_NAMES}} for the time today. Helpful conversation — particularly around {{ONE_SPECIFIC_TOPIC_RAISED — e.g., "tenant isolation and the per-tenant data encryption key model" or "how the recovery verification artifact would map to your SOC 2 evidence pack"}}.
>
> A short summary of what we covered and where things stand:
>
> - **Security model and controls**: covered on the public security page, including the tenant data handling lifecycle and the procurement FAQ. <https://kavachiq.com/security>
> - **Compliance mapping** ({{FRAMEWORKS_DISCUSSED — e.g., "SOC 2, HIPAA, and DORA"}}): mapped controls are documented; formal artifacts route through security@kavachiq.com
> - **Open requests**: {{LIST_OPEN_ITEMS — e.g., "your team's vendor-risk questionnaire (response targeted within {{TIMEFRAME}})", "a draft DPA for legal review", "BAA review for your healthcare workloads"}}
>
> What we'll do next:
>
> 1. {{ACTION_1 — e.g., "Send your completed vendor-risk questionnaire to {{REVIEWER_NAME}} by {{DATE}}"}}
> 2. {{ACTION_2 — e.g., "Route the draft DPA through your legal team for review"}}
> 3. {{ACTION_3 — optional, e.g., "Coordinate a follow-up call with {{NAMED_STAKEHOLDER}} once questionnaire feedback is in"}}
>
> If your team needs additional artifacts ahead of a final review meeting, the fastest path is security@kavachiq.com. Typical reply within one business day.
>
> Best,
> {{YOUR_NAME}}
> KavachIQ · security@kavachiq.com

### Pairs with
- `/security` — the canonical reference for everything covered in a security review
- `security@kavachiq.com` — the routing path for every artifact request that surfaces during the review
- `recovery-brief-template.md` — the brief gives security reviewers the operational context they often want alongside the controls discussion
- `/overview` — for procurement teams who need a one-page summary to share with their decision-maker

---

## Personalization checklist before sending

- [ ] Subject line includes the account name (or buyer first name) — generic subjects get ignored
- [ ] Opening sentence references something specific the buyer said
- [ ] All `{{...}}` placeholders filled or removed (no template artifacts left in the email)
- [ ] One concrete next step with a proposed time window
- [ ] Right scenario URL for this buyer, not a generic `/scenarios` link unless you genuinely don't know which one
- [ ] Logged in CRM with which template, which URLs, and which next-step ask was sent

---

## Things to avoid

- **Reciting features**. The buyer already saw the demo. Recap what mattered to them, not what was on the slide.
- **Multiple next-step asks**. Pick one. "Want a demo, a security review, or a follow-up call?" lands as zero asks.
- **Manufactured urgency**. "Limited spots", "before Q-end", "early-access pricing" all violate the locked GTM.
- **Pricing in the body**. Pricing belongs in a separately scoped conversation. Do not anchor in a follow-up.
- **Long-form thought leadership in the email**. If the recap needs that depth, send the recovery brief or link to a scenario page.
- **CC'ing internal stakeholders the buyer hasn't met**. Cold-add via separate intro, not a forced CC.
- **Pasting the same email twice**. If you've already sent template 1, do not re-send it after the next call. Move to template 2.

---

## Adapting by buyer type

| Buyer | Lean toward |
|---|---|
| **M365 admin / Entra admin** | Template 1 or 2. Recap operational specifics. Short and direct. |
| **IT or security leader** | Template 2. Recap recovery-order and verification. Pair with the recovery brief. |
| **Procurement / risk reviewer** | Template 3. Recap controls, mapped frameworks, and route artifact requests through security@. |
| **Champion who needs to brief their CISO/CIO** | Template 1 or 2 with `/overview` linked prominently. Make it easy to forward. |

---

## How these templates fit the rest of `docs/sales/`

- **`outreach-templates.md`** handles cold first contact (LinkedIn, intro emails). **`follow-up-email-templates.md`** (this file) takes over after the first conversation has happened.
- **`founder-demo-script.md`** ends with "always send the follow-up email within 2 hours of the call" — these are those emails.
- **`recovery-brief-template.md`** is the structured artifact for serious follow-up. Use it alongside template 1 or 2 when the call warranted it; pure email is enough when it did not.
- **`discovery-questions.md`** answers feed both this email's recap and the recovery brief sections.
- **`objection-handling.md`** — if a real objection surfaced during the call, address it briefly in the email and link the relevant proof asset; the full objection-handling pattern stays a live-call tool.

---

*Keep the templates in sync with the public site and the rest of `docs/sales/`. If a scenario URL, capability name, or contact path shifts on `/welcome`, `/scenarios/*`, `/security`, or `/overview`, update the references here so the email and the live page stay aligned.*
