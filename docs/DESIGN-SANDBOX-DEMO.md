# KavachIQ — Sandbox & Demo Strategy

## Author
Principal Product Manager | April 2026

## Problem

Three audiences need to see KavachIQ's onboarding experience:

1. **Internal testing** — developers verifying onboarding flow after code changes
2. **Sales demos** — showing prospects the full journey from zero to protected
3. **Website visitors** — async product exploration without signup

Each requires a different level of "fresh start."

## Competitive Research

| Product | Demo Approach | Self-Service? |
|---------|--------------|---------------|
| **Salesforce** | Full sandbox copies (4 tiers: Dev, Dev Pro, Partial, Full) | Enterprise plan only |
| **HubSpot** | Sandbox accounts with metadata sync, no pre-seeded data | Enterprise plan only |
| **Datadog** | 14-day trial, prospect instruments own stack. Conference demos use dedicated demo app | No sandbox |
| **Stripe** | Test/live mode toggle — same app, `livemode` boolean on every record | Built-in |
| **Veeam/Druva/Rubrik** | No self-service demo. Live demos by SEs against test M365 tenants | No |

**Key insight**: No backup product offers self-service demos. An interactive demo or seed-data approach would differentiate KavachIQ immediately.

## Three-Phase Strategy

### Phase 1: Reset Endpoints (Shipped ✅)

**For internal testing.** Admin can reset any user to see onboarding fresh.

**Full reset** clears 3 things:
1. Onboarding steps (server-side immutable records)
2. Tenant membership (so `has_tenants=false` → onboarding wizard appears)
3. User preferences (checklist_dismissed, selected_tenant)

```bash
# Reset a user to day-zero (admin only)
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.kavachiq.com/api/onboard/steps/reset/demo?full=true"

# Next login → user sees "Connect Microsoft 365" wizard
```

**Partial reset** clears only onboarding steps (user keeps tenant):
```bash
curl -X DELETE -H "Authorization: Bearer $ADMIN_TOKEN" \
  "https://api.kavachiq.com/api/onboard/steps/reset/demo"

# Next login → user sees checklist on dashboard (5/6 from fallback)
```

### Phase 2: Seed Data Script (Before First Paid Customer)

**For sales demos.** Create a realistic demo environment in one command.

```bash
./scripts/create-demo-tenant.sh "Acme Corp" acme-demo
```

This creates:
- A new user (`acme-demo`) with temporary password
- A simulated tenant ("Acme Corp") with realistic fake data
- Pre-populated objects: 25 mailboxes, 10 SharePoint sites, 5 Teams
- Simulated backup history (30 days of successful backups)
- Health score at 85, Recovery Confidence at 70
- A few deliberate "issues" to show Smart Engine value:
  - 2 anomalies (demonstrates detection)
  - 1 failed item (demonstrates resolution guidance)
  - 1 unprotected mailbox (demonstrates protection gaps)

The demo prospect logs in and sees a fully operational product with real-looking data.

**Implementation**: A Python script that uses the existing seed module pattern — creates DB records directly, no actual M365 connection needed.

### Phase 3: Interactive Demo Tool (For Website)

**For website visitors.** Embed on kavachiq.com landing page.

Use Storylane or Navattic ($40-100/month) to capture the real KavachIQ UI and make it clickable. Prospects can explore the product without signup.

**Why this works for backup products**: Veeam, Druva, and Rubrik all rely on recorded video demos or live SE walkthroughs. A clickable interactive demo is already differentiated.

**Embed on**:
- Landing page "See It In Action" button
- Product Tour page
- Pricing page ("Preview before you buy")

## Architecture Decision: Why NOT Stripe's Test/Live Model

Stripe's `livemode` boolean works because:
- Their product is an API — the "UI" is mostly the developer's integration
- Test transactions have no side effects (no money moves)
- The data model is simple (charges, customers, subscriptions)

For a backup product:
- Backups have real side effects (storage consumption, Graph API calls)
- The data model is complex (tenants, objects, snapshots, items, jobs)
- A "test mode" would need to simulate the entire Graph API → storage pipeline
- Cost of maintaining a parallel data partition exceeds the benefit

**Decision**: Use seed data (Phase 2) instead of data partitioning. Simpler, faster, and the demo tenant can be deleted cleanly.

## Reset Endpoint Specification

### DELETE /api/onboard/steps/reset/{username}

**Query params:**
- `full=true` — full reset (steps + tenant membership + preferences)
- Default — partial reset (steps only)

**Full reset behavior:**
1. Delete all onboarding_steps for the user
2. Delete all user_tenant memberships for the user
3. Delete user preferences (checklist_dismissed, selected_tenant)
4. User's next login → session returns `has_tenants=false` → redirected to onboarding wizard

**Partial reset behavior:**
1. Delete all onboarding_steps for the user
2. Keep tenant membership and preferences
3. User's next login → dashboard with onboarding checklist (frontend fallback derives steps from session)

**Security:**
- Platform admin (`username=admin`) only
- Cannot reset the admin user themselves
- Audit logged

## Cost Estimate

| Phase | Effort | Cost |
|-------|--------|------|
| Phase 1: Reset endpoints | Done ✅ | $0 |
| Phase 2: Seed data script | 2-3 days | $0 |
| Phase 3: Interactive demo | 1 day setup | $40-100/month |
