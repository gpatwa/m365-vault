# Shieldio — Feature Flag Architecture & Decision Record

**Date: 2026-03-31 | Status: Implemented (v1) + Future Migration Path**

---

## 1. Decision: Config-Based Feature Flags (Not LaunchDarkly)

### Context

Shieldio needs feature gating for two reasons:
1. **Pricing enforcement** — different tiers unlock different features
2. **Production readiness** — enable/disable features before they're ready for customers

### Options Evaluated

| Option | Cost | Ops Overhead | Right Stage |
|--------|------|-------------|-------------|
| **Config-based (what we built)** | $0 | None | 0-50 customers |
| **Flipt** (open-source, self-hosted) | $0 | Low (single binary) | 50-200 customers |
| **ConfigCat** (managed SaaS) | $18/mo | None | 200+ customers |
| **Unleash** (open-source, self-hosted) | $0 (CE) | Medium (needs infra) | 200+ customers |
| **Flagsmith** (open-source + cloud) | $0-99/mo | Low-Medium | 100+ customers |
| **GrowthBook** (open-source) | $0 | Medium | When A/B testing needed |
| **PostHog** (all-in-one) | $0-based | Medium | When analytics + flags needed |
| **LaunchDarkly** (enterprise SaaS) | $10K+/yr | None | 1000+ customers, 50+ engineers |

### Decision

**Config-based feature flags tied to the pricing engine.** Reasons:

1. **Zero cost, zero dependency** — no external service to manage, no API latency
2. **Tier-based gating is our primary use case** — features unlock based on pricing tier
3. **Admin overrides for demos/pilots** — force-enable features for prospects
4. **Already integrated** — flags checked in backend middleware + frontend context
5. **LaunchDarkly is massive overkill** — designed for 100 deploys/day, 50+ engineers, complex A/B testing. We have 1 engineer and 0 customers.

### Migration Trigger

Upgrade to **Flipt** when ANY of these are true:
- 50+ customers need percentage-based feature rollouts
- Multiple engineers need independent feature flag management
- Canary deployments require gradual traffic shifting
- A/B testing beyond simple on/off is needed

Upgrade to **ConfigCat** when:
- Team wants zero-ops managed solution
- 200+ customers across multiple tiers
- Need flag change audit trail beyond what we track

**Do NOT adopt LaunchDarkly** unless:
- 500+ customers AND 10+ engineers AND budget for $10K+/year

---

## 2. Current Architecture (v1 — Config-Based)

### How It Works

```
┌──────────────────────────┐     ┌──────────────────────────┐
│  LICENSE_TIER = "business"│     │  FEATURE_OVERRIDES env   │
│  (from config.py / .env) │     │  "+msp_demo,-cleanroom"  │
└────────────┬─────────────┘     └────────────┬─────────────┘
             │                                │
             ▼                                ▼
      ┌──────────────────────────────────────────────┐
      │         FeatureFlagService                    │
      │  ┌─────────────────────────────────────────┐  │
      │  │  TIER_FEATURES[tier] + _overrides       │  │
      │  │  is_enabled("msp_dashboard") → True     │  │
      │  └─────────────────────────────────────────┘  │
      └──────────┬───────────────────┬────────────────┘
                 │                   │
        ┌────────▼───────┐  ┌───────▼────────┐
        │  Backend API   │  │  Frontend      │
        │  Middleware     │  │  FeatureGate   │
        │  Route guards  │  │  Component     │
        └────────────────┘  └────────────────┘
```

### Feature Categories

| Category | Features | Controls |
|----------|----------|----------|
| **Workloads** | exchange, onedrive, sharepoint, teams, entra_id, power_platform | Which M365 workloads can be backed up |
| **Intelligence** | anomaly_detection, health_scoring, sensitive_data_scanner, org_context, mvb_plans, criticality_scoring | Smart Engine features |
| **Recovery** | mass_recovery, test_restore, agentic_recovery, cleanroom | Recovery capabilities |
| **Compliance** | worm, legal_hold, ediscovery | Compliance features |
| **Operations** | msp_dashboard, msp_billing, msp_branding, msp_bulk_onboard, msp_demo | MSP management features |
| **Platform** | api_access, sso, webhooks, custom_reports | Platform capabilities |

### Tier Matrix

| Feature | Community | Professional | Business | Enterprise |
|---------|-----------|-------------|----------|-----------|
| **exchange** | Yes | Yes | Yes | Yes |
| **onedrive** | Yes | Yes | Yes | Yes |
| **sharepoint** | Yes | Yes | Yes | Yes |
| **teams** | — | Yes | Yes | Yes |
| **entra_id** | — | Yes | Yes | Yes |
| **power_platform** | — | — | — | Yes |
| **anomaly_detection** | Yes | Yes | Yes | Yes |
| **health_scoring** | — | Yes | Yes | Yes |
| **sensitive_data_scanner** | — | Yes | Yes | Yes |
| **org_context** | — | — | Yes | Yes |
| **mvb_plans** | — | — | Yes | Yes |
| **criticality_scoring** | — | — | Yes | Yes |
| **mass_recovery** | Yes | Yes | Yes | Yes |
| **test_restore** | — | Yes | Yes | Yes |
| **agentic_recovery** | — | — | — | Yes |
| **cleanroom** | — | — | — | Yes |
| **worm** | — | — | Yes | Yes |
| **legal_hold** | — | — | Yes | Yes |
| **ediscovery** | — | — | — | Yes |
| **msp_dashboard** | — | — | Yes | Yes |
| **msp_billing** | — | — | Yes | Yes |
| **msp_branding** | — | — | — | Yes |
| **msp_bulk_onboard** | — | — | — | Yes |
| **msp_demo** | — | — | — | Yes |
| **api_access** | Yes | Yes | Yes | Yes |
| **sso** | — | Yes | Yes | Yes |
| **webhooks** | — | — | Yes | Yes |
| **custom_reports** | — | — | — | Yes |

### Tier Limits

| Limit | Community | Professional | Business | Enterprise |
|-------|-----------|-------------|----------|-----------|
| Max protected objects | 25 | Unlimited | Unlimited | Unlimited |
| Max tenants | 1 | 10 | Unlimited | Unlimited |
| Max workloads | 3 | 5 | Unlimited | Unlimited |
| Retention days | 30 | 90 | 365 | 365 |

---

## 3. API Reference

### Public Endpoints (No Auth)

```
GET /api/features
  → { tier, features: { feature_name: { enabled, source } }, limits, overrides }

GET /api/features/check/{feature}
  → { feature, enabled, tier }
```

### Admin Endpoints (Auth Required)

```
GET /api/features/categories
  → { tier, categories: { workloads: {exchange: true, ...}, ... }, limits }

GET /api/features/tiers
  → { current_tier, comparison: { feature_name: { community: false, professional: true, ... } } }

PUT /api/features/override
  Body: { "feature": "msp_dashboard", "enabled": true }
  → { feature, enabled, source: "override" }

DELETE /api/features/override/{feature}
  → { feature, enabled, source: "tier:business" }
```

### Environment Variable

```bash
# Force enable/disable features regardless of tier
# Format: "+feature1,-feature2,+feature3"
FEATURE_OVERRIDES="+msp_dashboard,+msp_demo,-cleanroom"
```

---

## 4. Frontend Usage

### FeatureFlagContext

```tsx
// Available app-wide via context
const { isEnabled, tier, flags, limits } = useFeatureFlags();

// Check a specific feature
if (isEnabled('msp_dashboard')) {
  // show MSP nav
}
```

### FeatureGate Component

```tsx
// Declarative gating — only renders children if feature is enabled
<FeatureGate feature="org_context">
  <OrgContextPage />
</FeatureGate>

// With fallback for disabled features
<FeatureGate feature="worm" fallback={<UpgradePrompt tier="business" />}>
  <WORMSettings />
</FeatureGate>
```

### Admin UI

`/features` page (admin only):
- Category view: all features with enabled/disabled status
- Toggle buttons to force-enable or force-disable (admin override)
- Tier comparison tab: see what each tier includes
- Current tier + limits display

---

## 5. How to Use for Production Readiness

### Scenario: Gate MSP features for pilot MSPs only

```bash
# Set tier to professional (no MSP features by default)
LICENSE_TIER=professional

# Force-enable MSP dashboard for the pilot
FEATURE_OVERRIDES="+msp_dashboard,+msp_billing"
```

### Scenario: Disable a broken feature without redeploying

```bash
# Admin API call — no deploy needed
curl -X PUT /api/features/override \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"feature": "anomaly_detection", "enabled": false}'
```

### Scenario: Demo mode with all features enabled

```bash
LICENSE_TIER=enterprise
# Enterprise tier enables everything — no overrides needed
```

### Scenario: Upgrade a customer from Professional to Business

```bash
# Change the tier setting (requires restart or config reload)
LICENSE_TIER=business

# Or temporarily via override (no restart)
FEATURE_OVERRIDES="+org_context,+mvb_plans,+criticality_scoring,+worm,+msp_dashboard,+msp_billing"
```

---

## 6. Future Migration Path

### Phase 1: Current (0-50 customers)
**Config-based** — tier determines features, admin overrides for exceptions.

### Phase 2: Flipt (50-200 customers)
When percentage rollouts or per-customer targeting is needed:
- Deploy Flipt as a Docker sidecar (single Go binary, minimal footprint)
- Migrate TIER_FEATURES to Flipt segments
- Keep FeatureFlagService as abstraction layer — swap backend from config to Flipt API
- Estimated migration: 2-3 days

### Phase 3: ConfigCat or Flagsmith (200+ customers)
When managed solution with audit trail is needed:
- ConfigCat: $18/mo, zero-ops, flat pricing
- Flagsmith: open-source with managed cloud option
- Same abstraction layer — swap backend again

### Never: LaunchDarkly
Unless: 500+ customers, 10+ engineers, $10K+ budget, complex multi-team flag management.

---

## 7. Files

| File | Purpose |
|------|---------|
| `backend/app/services/feature_flags.py` | FeatureFlagService, TIER_FEATURES matrix, override logic |
| `backend/app/api/feature_flags.py` | REST API (6 endpoints) |
| `backend/app/config.py` | `LICENSE_TIER`, `FEATURE_OVERRIDES` settings |
| `frontend/src/contexts/FeatureFlagContext.tsx` | React context + `useFeatureFlags()` hook + `FeatureGate` component |
| `frontend/src/pages/FeatureFlags.tsx` | Admin UI at `/features` |

---

## Sources

- [Flagsmith: LaunchDarkly Alternatives](https://www.flagsmith.com/blog/launchdarkly-alternatives)
- [PostHog: Best Open-Source Feature Flag Tools](https://posthog.com/blog/best-open-source-feature-flag-tools)
- [Unleash vs LaunchDarkly](https://www.getunleash.io/unleash-vs-launchdarkly)
- [ConfigCat: Top Alternatives](https://configcat.com/blog/top-eight-launchdarkly-alternatives/)
- [Schematic: LaunchDarkly Alternatives 2026](https://schematichq.com/blog/launchdarkly-alternatives)
