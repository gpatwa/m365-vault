# KavachIQ Stripe Integration Plan

## Overview

Integrate Stripe Billing for self-serve subscription management, automated invoicing,
and MSP wholesale billing. Enables customers to sign up, pay, upgrade, and manage
subscriptions without manual intervention.

**Target**: Accept first payment within 2 weeks of implementation start.

---

## Architecture

```
Customer Browser                    KavachIQ Backend              Stripe
    |                                    |                          |
    |-- Click "Start Trial" ------------>|                          |
    |                                    |-- Create Customer ------>|
    |                                    |-- Create Subscription -->|
    |<-- Redirect to Checkout -----------|<-- Checkout Session -----|
    |                                    |                          |
    |-- Complete Payment (Stripe UI) --->|                          |
    |                                    |<-- webhook: invoice.paid |
    |                                    |   Activate license tier  |
    |                                    |                          |
    |-- Manage Subscription ------------>|                          |
    |<-- Redirect to Customer Portal ----|<-- Portal Session -------|
```

---

## Stripe Products & Prices

### Direct Customer Tiers

| Tier | Stripe Product | Price | Billing |
|---|---|---|---|
| Community | Free (no Stripe) | $0 | No payment required |
| Professional | `prod_professional` | $1.50/user/month | Monthly or Annual ($16.20/user/yr = 10% off) |
| Business | `prod_business` | $3.00/user/month | Monthly or Annual ($32.40/user/yr) |
| Enterprise | `prod_enterprise` | $5.00/user/month | Monthly or Annual ($54.00/user/yr) |

### MSP Wholesale Tiers

| Volume | Stripe Price | ID |
|---|---|---|
| 1-500 users | $1.50/user/month | `price_msp_tier1` |
| 501-2,000 | $1.25/user/month | `price_msp_tier2` |
| 2,001-5,000 | $1.00/user/month | `price_msp_tier3` |
| 5,001+ | $0.85/user/month | `price_msp_tier4` |

---

## Implementation Phases

### Phase 1: Stripe Setup & Checkout (Week 1)

**Backend: `backend/app/api/billing.py`** (new file)

```
POST /api/billing/checkout          -- Create Stripe Checkout Session
POST /api/billing/portal            -- Create Stripe Customer Portal session
POST /api/billing/webhook           -- Handle Stripe webhooks
GET  /api/billing/subscription      -- Get current subscription status
POST /api/billing/usage-report      -- Report metered usage to Stripe
```

**Key endpoints:**

1. **Checkout Session** — When user clicks "Start Trial" or "Upgrade":
   - Create Stripe Customer (link to KavachIQ user)
   - Create Checkout Session with selected price
   - Include 14-day free trial for Professional/Business
   - Return checkout URL for redirect

2. **Webhook Handler** — Process Stripe events:
   - `checkout.session.completed` → activate subscription, set license tier
   - `invoice.paid` → extend subscription period
   - `invoice.payment_failed` → send warning, grace period (7 days)
   - `customer.subscription.updated` → handle upgrade/downgrade
   - `customer.subscription.deleted` → downgrade to Community

3. **Customer Portal** — Self-serve management:
   - Update payment method
   - View invoices
   - Upgrade/downgrade plan
   - Cancel subscription

**Database changes:**

```sql
ALTER TABLE users ADD COLUMN stripe_customer_id VARCHAR(255);
ALTER TABLE tenants ADD COLUMN stripe_subscription_id VARCHAR(255);
ALTER TABLE tenants ADD COLUMN subscription_status VARCHAR(50) DEFAULT 'free';
ALTER TABLE tenants ADD COLUMN subscription_tier VARCHAR(50) DEFAULT 'community';
ALTER TABLE tenants ADD COLUMN trial_ends_at TIMESTAMP;
ALTER TABLE tenants ADD COLUMN current_period_end TIMESTAMP;
```

**Environment variables:**
```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_PROFESSIONAL_MONTHLY=price_...
STRIPE_PRICE_PROFESSIONAL_ANNUAL=price_...
STRIPE_PRICE_BUSINESS_MONTHLY=price_...
STRIPE_PRICE_BUSINESS_ANNUAL=price_...
STRIPE_PRICE_ENTERPRISE_MONTHLY=price_...
STRIPE_PRICE_ENTERPRISE_ANNUAL=price_...
```

### Phase 2: Frontend Integration (Week 1)

**Pricing page CTAs** — Update Landing.tsx:
- "Start Free" → creates account, no payment
- "Start Trial" (Professional) → redirects to Stripe Checkout with 14-day trial
- "Start Trial" (Business) → same with Business price
- "Contact Sales" (Enterprise) → Calendly/email link

**Dashboard upgrade banner** — When approaching Community limits:
- "You're using 20/25 objects. Upgrade to Professional for unlimited."
- Click → Stripe Checkout

**Settings > Billing page** — New page `frontend/src/pages/Billing.tsx`:
- Current plan display
- Usage vs limits
- "Manage Subscription" → Stripe Customer Portal
- Invoice history (from Stripe API)
- Payment method on file

### Phase 3: License Enforcement (Week 2)

**Connect Stripe subscription to license tiers:**

```python
# backend/app/middleware/license.py
async def check_license(tenant_id: int, db: AsyncSession):
    tenant = await db.get(Tenant, tenant_id)
    if tenant.subscription_status == 'active':
        return LICENSE_TIERS[tenant.subscription_tier]
    if tenant.subscription_status == 'trialing':
        return LICENSE_TIERS[tenant.subscription_tier]  # full access during trial
    if tenant.subscription_status == 'past_due':
        return LICENSE_TIERS[tenant.subscription_tier]  # grace period
    return LICENSE_TIERS['community']  # default fallback
```

**Soft limits (warn) vs Hard limits (block):**
- Community 25 objects: soft limit — warn at 20, block new protection at 26
- Tenant count: soft limit — warn at 80%, block at limit
- Workload count: hard limit per tier
- Retention: enforce on backup cleanup, not on restore

### Phase 4: MSP Billing (Week 2)

**Connect existing MSP billing to Stripe:**
- MSP partners get a single Stripe subscription
- Metered billing based on total managed users
- Monthly usage report via `POST /api/billing/usage-report`
- Stripe calculates tiered wholesale pricing automatically

**Stripe Metered Billing setup:**
```
Product: MSP Wholesale
Price: Graduated pricing
  Tier 1: First 500 units at $1.50/unit
  Tier 2: Next 1,500 units at $1.25/unit
  Tier 3: Next 3,000 units at $1.00/unit
  Tier 4: Above 5,000 units at $0.85/unit
Billing: Monthly, in arrears
```

### Phase 5: Stripe Tax (Week 3)

**Enable automatic tax calculation:**
- Stripe Tax: 0.5% per transaction
- Automatically calculates US sales tax per state
- Handles EU VAT for international customers
- No need to register in every state initially (economic nexus threshold)

**Configuration:**
```python
stripe.checkout.Session.create(
    automatic_tax={'enabled': True},
    ...
)
```

### Phase 6: Trial Management (Week 3)

**14-day trial flow:**
1. User signs up → Community tier (no payment)
2. User clicks "Start Trial" → Stripe Checkout with `trial_period_days=14`
3. During trial: full Professional/Business access
4. Day 12: email reminder "Trial ends in 2 days"
5. Day 14: auto-charge if card on file, or downgrade to Community

**Trial-to-paid conversion tracking:**
- PostHog event: `trial.started`, `trial.converted`, `trial.expired`
- Webhook: `customer.subscription.trial_will_end` → send reminder email

---

## Webhook Events to Handle

| Event | Action |
|---|---|
| `checkout.session.completed` | Create/update subscription, set tier |
| `customer.subscription.created` | Log in audit, send welcome email |
| `customer.subscription.updated` | Update tier if plan changed |
| `customer.subscription.deleted` | Downgrade to Community |
| `customer.subscription.trial_will_end` | Send trial ending reminder (3 days before) |
| `invoice.paid` | Update `current_period_end`, log payment |
| `invoice.payment_failed` | Set `past_due`, send retry email |
| `invoice.finalized` | Store invoice PDF URL |

---

## Security

- Stripe secret key stored in Azure Key Vault (not in code)
- Webhook signature verification on every request
- No credit card data touches KavachIQ servers (Stripe Checkout handles PCI)
- Customer Portal for self-serve card management (no card storage needed)
- Audit log entry for every billing event

---

## Revenue Metrics (Automated)

After Stripe integration, these metrics are available automatically:
- **MRR/ARR**: Stripe Dashboard or API
- **Churn rate**: Subscription cancellation events
- **Trial conversion**: trial → paid ratio
- **ARPU**: Revenue / active customers
- **LTV**: ARPU x average lifetime
- **Revenue by tier**: Stripe product reports

---

## Cost

| Item | Cost |
|---|---|
| Stripe processing | 2.9% + 30¢ per transaction |
| Stripe Billing | +0.7% per invoice |
| Stripe Tax | +0.5% per transaction (optional) |
| **Total per $1.50 transaction** | ~$0.11 (7.3%) |
| **Total per $3.00 transaction** | ~$0.16 (5.3%) |
| **Total per $5.00 transaction** | ~$0.22 (4.4%) |

At 100 Professional customers ($1.50 x 100 users avg = $150/mo each):
- Monthly revenue: $15,000
- Stripe fees: ~$1,095 (7.3%)
- Net: $13,905

---

## Files to Create/Modify

| File | Action |
|---|---|
| `backend/app/api/billing.py` | **New** — Checkout, portal, webhook, subscription endpoints |
| `backend/app/models/tenant.py` | **Modify** — Add stripe_customer_id, subscription fields |
| `backend/app/models/user.py` | **Modify** — Add stripe_customer_id |
| `frontend/src/pages/Billing.tsx` | **New** — Subscription management page |
| `frontend/src/pages/Landing.tsx` | **Modify** — Connect CTAs to Stripe Checkout |
| `frontend/src/pages/Usage.tsx` | **Modify** — Add upgrade button linking to Checkout |
| `frontend/src/components/Layout.tsx` | **Modify** — Add Billing to sidebar nav |
| `infra/` | **Modify** — Add STRIPE env vars to Container Apps |
| `requirements.txt` | **Modify** — Add `stripe` Python package |

---

## Timeline

| Week | Milestone |
|---|---|
| Week 1 | Stripe account setup, products/prices created, checkout + webhook + portal endpoints |
| Week 1 | Frontend billing page, pricing CTA updates, upgrade banners |
| Week 2 | License enforcement connected to Stripe subscription status |
| Week 2 | MSP metered billing connected to Stripe |
| Week 3 | Stripe Tax enabled, trial management flow |
| Week 3 | End-to-end testing: signup → trial → pay → upgrade → cancel |
