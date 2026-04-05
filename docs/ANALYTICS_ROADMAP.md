# KavachIQ Analytics Roadmap — PostHog + Plausible + Clarity

## Overview

Privacy-first analytics stack for a data protection product. Self-hosted where possible.
Total cost: **$0/month** at launch.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Landing Page                      │
│              (/welcome, /login, /legal)              │
│                                                      │
│   Plausible (pageviews, referrers, conversions)      │
│   Microsoft Clarity (heatmaps, session replay)       │
└──────────────────────┬──────────────────────────────┘
                       │ User logs in
                       ▼
┌─────────────────────────────────────────────────────┐
│                 Product App                           │
│    (Dashboard, Workloads, Recovery, Onboarding)       │
│                                                      │
│   PostHog (events, funnels, retention, replay)        │
│   PostHog Feature Flags (gradual rollout)             │
└──────────────────────┬──────────────────────────────┘
                       │ API calls
                       ▼
┌─────────────────────────────────────────────────────┐
│                 Backend (FastAPI)                     │
│                                                      │
│   PostHog Python SDK (server-side events)             │
│   - backup.completed, restore.executed                │
│   - anomaly.detected, tenant.onboarded                │
└─────────────────────────────────────────────────────┘
```

---

## Phase 1: Plausible (Landing Page Analytics) — Day 1

### What
Self-hosted Plausible for cookieless website analytics on the landing/marketing pages.

### Why First
- Zero-config, single script tag
- No cookies = no consent banner needed
- Instant value: see visitor count, referrers, conversions

### Implementation

**Infrastructure** — Add to `docker-compose.yml`:
```yaml
plausible:
  image: ghcr.io/plausible/community-edition:v2
  platform: linux/amd64
  ports:
    - "8100:8000"
  environment:
    - BASE_URL=http://localhost:8100
    - SECRET_KEY_BASE=<generate-64-char-secret>
    - DATABASE_URL=postgres://postgres:postgres@postgres:5432/plausible
    - CLICKHOUSE_DATABASE_URL=http://clickhouse:8123/plausible
  depends_on:
    - postgres
    - clickhouse

clickhouse:
  image: clickhouse/clickhouse-server:24-alpine
  platform: linux/amd64
  volumes:
    - clickhouse_data:/var/lib/clickhouse
```

**Frontend** — Add script tag to `index.html` (landing pages only):
```html
<script defer data-domain="kavachiq.com" src="http://localhost:8100/js/script.js"></script>
```

**Goals to track**:
- `Start Free` button click
- `Sign In` navigation
- `Book a Demo` click
- Pricing section scroll
- FAQ expansion

### Metrics
- Unique visitors / day
- Top referral sources
- Landing → Login conversion rate
- Bounce rate by section
- Geographic distribution

---

## Phase 2: Microsoft Clarity (Heatmaps + Replay) — Day 1

### What
Free unlimited session replay and heatmaps for the landing page.

### Why
- See exactly where users click, scroll, and drop off
- Rage click detection finds UX frustrations
- Zero cost, unlimited sessions
- Dead click detection

### Implementation

**Frontend** — Add Clarity script to `index.html`:
```html
<script type="text/javascript">
  (function(c,l,a,r,i,t,y){
    c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};
    t=l.createElement(r);t.async=1;t.src="https://www.clarity.ms/tag/"+i;
    y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);
  })(window,document,"clarity","script","YOUR_CLARITY_ID");
</script>
```

**Configuration**:
- Enable only on public pages (/welcome, /login, /legal)
- Disable on authenticated app pages (privacy — don't record tenant data)
- Set up custom tags: `page_type`, `user_type` (anonymous/authenticated)

### Metrics
- Heatmaps: click, scroll, area maps per page
- Session recordings: watch real user journeys
- Rage clicks: identify frustrating UI elements
- Dead clicks: buttons that look clickable but aren't
- Scroll depth: how far users read the landing page

---

## Phase 3: PostHog (Product Analytics) — Week 1

### What
Self-hosted PostHog for in-app product analytics, funnels, retention, and feature flags.

### Why PostHog
- Self-hosted = all data stays in your infra (critical for a security product)
- Replaces 4 tools: Mixpanel + LaunchDarkly + Hotjar + surveys
- 1M events/month free, 5K session recordings/month free
- React SDK with autocapture

### Implementation

**Infrastructure** — Docker Compose (dev) or Kubernetes (prod):
```yaml
# Dev: use PostHog Docker compose
# See: https://posthog.com/docs/self-host
# Requires: PostgreSQL, Redis, Kafka, ClickHouse, PostHog workers
```

For production (Azure): Deploy PostHog Helm chart on AKS, or use PostHog Cloud
free tier initially and migrate to self-hosted when needed.

**Frontend** — `frontend/src/analytics/posthog.ts`:
```typescript
import posthog from 'posthog-js'

export function initPostHog() {
  if (typeof window === 'undefined') return
  posthog.init('phc_YOUR_PROJECT_KEY', {
    api_host: 'https://analytics.kavachiq.com', // self-hosted
    autocapture: true,          // auto-track clicks, pageviews
    capture_pageview: true,
    capture_pageleave: true,
    session_recording: {
      maskAllInputs: true,       // mask passwords, emails
      maskTextSelector: '[data-mask]', // mask sensitive data
    },
    persistence: 'localStorage', // no cookies
  })
}

export function identifyUser(userId: string, traits: Record<string, any>) {
  posthog.identify(userId, traits)
}

export function trackEvent(event: string, properties?: Record<string, any>) {
  posthog.capture(event, properties)
}
```

**Backend** — `backend/app/analytics.py`:
```python
from posthog import Posthog

posthog_client = Posthog(
    api_key='phc_YOUR_PROJECT_KEY',
    host='https://analytics.kavachiq.com'
)

def track_server_event(user_id: str, event: str, properties: dict = None):
    posthog_client.capture(user_id, event, properties or {})
```

### Events to Track

**Onboarding Funnel**:
| Event | Properties |
|---|---|
| `onboard.started` | tenant_name, user_role |
| `onboard.tenant_connected` | platform (m365/google) |
| `onboard.workloads_discovered` | workload_count, workload_types[] |
| `onboard.protection_assigned` | sla_policy, object_count |
| `onboard.intelligence_viewed` | critical_count, total_users |
| `onboard.backup_started` | workload_types[] |
| `onboard.backup_completed` | duration_seconds, object_count |
| `onboard.recovery_plan_generated` | object_count, phases |
| `onboard.recovery_executed` | object_count, success |
| `onboard.completed` | total_duration_seconds |

**Product Usage**:
| Event | Properties |
|---|---|
| `backup.triggered` | workload, tenant_id, trigger (manual/scheduled) |
| `backup.completed` | workload, item_count, size_bytes, duration_s |
| `backup.failed` | workload, error_code, retriable |
| `restore.initiated` | workload, restore_type, item_count |
| `restore.completed` | workload, items_restored, duration_s |
| `anomaly.detected` | severity, workload, metric |
| `recovery_plan.viewed` | confidence_score, grade |
| `search.performed` | query_length, workload_filter, result_count |
| `page.viewed` | page_name, tenant_id |

**Engagement**:
| Event | Properties |
|---|---|
| `feature.used` | feature_name (smart_engine, org_context, etc.) |
| `dashboard.loaded` | health_score, protection_pct |
| `msp.tenant_managed` | action (onboard/offboard), tenant_count |
| `export.downloaded` | report_type (compliance, audit) |

### Funnels to Build in PostHog

1. **Signup → First Backup**: Login → Connect Tenant → Discover → Protect → Backup
2. **Recovery Readiness**: View Recovery → Generate Plan → Execute Recovery
3. **Feature Adoption**: Dashboard → Smart Engine → Org Context → Recovery
4. **Retention**: Weekly active users who run at least 1 backup

### Feature Flags (PostHog built-in)

| Flag | Purpose |
|---|---|
| `new-onboarding-flow` | A/B test onboarding variations |
| `show-pricing-v2` | Test new pricing page |
| `enable-agentic-recovery` | Gradual rollout of AI features |
| `msp-dashboard-v2` | Beta test MSP redesign |

---

## Phase 4: Google Search Console — Week 1

### What
Free SEO monitoring — how people find KavachIQ via Google.

### Implementation
1. Verify domain ownership (DNS TXT record)
2. Submit sitemap.xml
3. Monitor weekly

### Metrics
- Search queries driving traffic
- Click-through rate by keyword
- Average position for target keywords
- Indexing status
- Core Web Vitals

---

## Phase 5: Custom Analytics Dashboard — Month 1

### What
Build an internal analytics dashboard in KavachIQ admin that shows:
- Product health metrics from PostHog
- Landing page stats from Plausible
- Backup/restore trends from internal data

### Implementation
- PostHog API: `GET /api/insight/` for funnels and trends
- Plausible API: `GET /api/v1/stats/` for visitor data
- Internal: existing `/api/dashboard/summary` endpoint

---

## Privacy Architecture

### What Gets Tracked Where

| Data Type | Tool | Self-Hosted | PII |
|---|---|---|---|
| Landing page visits | Plausible | Yes | None — cookieless |
| Scroll/click heatmaps | Clarity | No (Microsoft) | Anonymized |
| Product events | PostHog | Yes | User ID only |
| Server-side events | PostHog | Yes | Tenant ID only |
| SEO performance | Search Console | No (Google) | None |

### What NEVER Gets Tracked
- Email content or subjects
- Backup data or snapshots
- Entra ID objects or configurations
- Passwords, tokens, or credentials
- Customer tenant data

### Privacy Controls
- PostHog: `maskAllInputs: true` — masks all form inputs in session replay
- Clarity: disabled on authenticated pages — only landing/login
- Plausible: cookieless by design — no consent banner needed
- All tools: respect Do Not Track header

---

## Cost Projection

| Tool | Now | 10K users | 100K users |
|---|---|---|---|
| Plausible (self-hosted) | $0 | $0 | $0 |
| Clarity | $0 | $0 | $0 |
| PostHog (self-hosted) | $0 | $0 (infra ~$50/mo) | $0 (infra ~$200/mo) |
| Search Console | $0 | $0 | $0 |
| **Total** | **$0** | **~$50** | **~$200** |

vs. Enterprise stack (GA4 + Amplitude + FullStory + Ahrefs): $500-5,000/month

---

## Implementation Timeline

| Week | Milestone |
|---|---|
| **Day 1** | Plausible script on landing page + Clarity script on landing page |
| **Day 2** | Google Search Console domain verification + sitemap |
| **Week 1** | PostHog React SDK in frontend with autocapture |
| **Week 1** | PostHog Python SDK in backend for server events |
| **Week 2** | Define and instrument 20 key events |
| **Week 2** | Build 4 funnels in PostHog |
| **Week 3** | Feature flags for A/B testing onboarding |
| **Month 1** | Internal analytics dashboard |
| **Month 2** | Retention cohorts + weekly metrics review |
| **Month 3** | Evaluate: add Ahrefs if SEO is a growth channel |

---

## Decision Log

| Decision | Rationale |
|---|---|
| Self-hosted PostHog over Mixpanel Cloud | Data sovereignty — critical for a security product |
| Plausible over GA4 | No cookies, no consent banner, brand alignment |
| Clarity over Hotjar | Free unlimited vs. $39/month, similar features |
| No Segment | PostHog handles data routing; Segment adds cost and complexity |
| No GA4 | Using Google tracking on a data protection product undermines trust |
| PostHog feature flags over LaunchDarkly | Bundled free, one less vendor |
