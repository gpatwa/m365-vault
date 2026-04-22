# Sales Asset Changelog

A short record of meaningful changes to `docs/sales/`. Add entries only for **strategically significant** sales-asset work. Skip routine typo fixes.

The companion to this file is [`README.md`](README.md), which always reflects the *current* state. This file explains *how* the current state was reached and *why* certain patterns are now off-limits.

---

## 2026-04 — Microsoft 365 rebrand and sales toolkit cleanup

The first generation of sales assets (vertical one-pagers, outreach templates, HIPAA blog) pre-dated the public Microsoft 365 rebrand. They led with pricing, free-tier hooks, anti-Microsoft framing, and "AI-powered" feature branding that contradicted the live site. This wave brought the entire `docs/sales/` folder onto the locked strategy and added the missing assets needed to run a founder-led sale end-to-end.

### What changed

**Assets rewritten to the locked strategy**
- `healthcare-one-pager.md`, `finance-one-pager.md`, `legal-one-pager.md` — repositioned around identity-first cyber recovery, dropped pricing-led structure, swapped "certified" claims for mapped-controls language. Each one-pager points at a different scenario URL so the trio reads as a coherent set, not a template clone.
- `outreach-templates.md` — all 7 LinkedIn / email templates rewritten to enterprise/demo-led motion. Removed "$1.50/user", "free for 25 users", "10-minute setup", "Microsoft's recycle bin..." hooks. Default landing changed from the dead `kavachiq.com/demo` URL to `/contact`.
- `hipaa-aware-m365-recovery.md` (formerly `blog-hipaa-recycle-bin.md`) — title and content repositioned from "Why Microsoft's Recycle Bin Fails Your HIPAA Audit" (anti-Microsoft hero) to "What HIPAA-Aware Teams Need from Microsoft 365 Recovery" (operational recovery framing). File renamed via `git mv` so history is preserved and the filename matches the current content.

**Assets added** (each shipped with its own canonical guardrail section)
- `founder-demo-script.md` — 30-min and 60-min call structures, openers by buyer type, discovery, demo flow, closing asks, and a "Things to avoid in the call" section.
- `recovery-brief-template.md` — fillable post-call artifact with eight sections and a "Things to never include" guard.
- `objection-handling.md` — eight high-frequency objections with good answers, proof URLs, and a "What not to say" section.
- `discovery-questions.md` — ~50-question pick-list across nine categories, plus "Don't interrogate the buyer" guardrails.
- `follow-up-email-templates.md` — three post-call templates (discovery, walkthrough, security review) with a "Things to avoid" section.
- `README.md` — entry-point index with a "use this when" table, sales motion by stage, asset-by-asset metadata, and a default 10-step founder-led flow.

**Naming cleanup**
- `blog-hipaa-recycle-bin.md` → `hipaa-aware-m365-recovery.md` (kebab-case, descriptive of current content, history-preserving rename).

### Canonical guardrails now in force

These guardrails are documented inside the assets themselves (each "What not to say" / "Things to never include" / "Things to avoid" section) and are enforced across every file in `docs/sales/`. They do not need re-stating in new assets, but new assets must comply.

- **Strategy**: KavachIQ for Microsoft 365 = identity-first cyber recovery for Microsoft Entra and Microsoft 365. Do not widen the story.
- **Primary CTA**: Request a Demo. Default URL: `https://kavachiq.com/contact`.
- **Forwardable one-pager URL**: `https://kavachiq.com/overview`. Do not produce a competing PDF version.
- **Compliance language**: mapped controls, not certified. Formal artifacts (SOC 2 report, BAA, DPA, vendor-risk questionnaire) route through `security@kavachiq.com`.
- **No anti-Microsoft hero framing.** Do not lead with "Microsoft doesn't back up...", "the recycle bin fails...", or anything similar. Acknowledge native and third-party tooling; position KavachIQ on top of them.
- **No pricing-led positioning.** No "$1.50/user", no "free for 25 users", no tier tables in any sales asset. Pricing belongs in a separate scoped conversation.
- **No PLG / freemium hooks.** No "Start Free", "free tier", "10-minute setup", "no credit card".
- **No open-source or self-hosted positioning.** Not part of the GTM.
- **No "AI-powered" or "Smart Engine" feature branding** in sales assets.
- **No exaggerated competitor attacks.** Speak about categories (native tools, generic backup, manual restore, broad cyber suites), not vendor names. Do not claim "no one else does this" without qualification.
- **No improvised features or commitments.** Customer-managed keys and multi-region per tenant are not public commitments today. Do not promise them. Route uncertainty through `security@`.
- **All asset CTAs route to live URLs.** No `kavachiq.com/demo` or other dead routes. The canonical public surfaces are `/welcome`, `/tour`, `/scenarios`, `/scenarios/*`, `/security`, `/overview`, and `/contact`.

### Result

After this wave, `docs/sales/` covers cold contact through second-call follow-up entirely on-strategy:

```
Cold contact      →  outreach-templates.md
Pre-call prep     →  founder-demo-script.md, discovery-questions.md
Live call         →  founder-demo-script.md, objection-handling.md
Post-call email   →  follow-up-email-templates.md
Post-call brief   →  recovery-brief-template.md
Vertical handoff  →  healthcare- / finance- / legal-one-pager.md
Long-form support →  hipaa-aware-m365-recovery.md
Index             →  README.md
```

Every CTA across every file routes to a real public URL, and zero off-strategy hooks remain in body content of any asset.

---

## How to use this changelog going forward

- **Add an entry** when you make a *strategically significant* sales-asset change: a new asset, a rewrite, a renamed file, a guardrail addition, or a deliberate retirement.
- **Skip routine edits.** Typos, formatting, link tweaks, and small wording polish do not warrant entries.
- **Keep entries dated and short.** A few bullets under "What changed" plus, if relevant, an addition to the "Canonical guardrails now in force" section.
- **Keep [`README.md`](README.md) aligned with the live site.** The README always reflects current state; this changelog explains how it got there and what is now off-limits.
- **If a new asset adds a new guardrail**, add it to the canonical list in this file. Future contributors should be able to read the most recent dated entry plus the canonical guardrails and avoid reintroducing patterns we have already removed.

---

*If you find a sales asset doing something that contradicts a guardrail above, the asset is wrong, not the guardrail. Open a small fix and add a one-line entry here.*
