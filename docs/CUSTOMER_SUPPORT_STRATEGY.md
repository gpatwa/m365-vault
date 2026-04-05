# KavachIQ — Customer Support Strategy

**Date: 2026-03-30 | Status: Strategy Document**

---

## 1. Competitor Support Models

### How Competitors Structure Support

| Vendor | Support Tiers | Sev-1 SLA | Premium Cost | Guarantee |
|--------|--------------|-----------|-------------|-----------|
| **Veeam** | Basic / Production / Premier | 30 min (Premier), 24/7 (Prod) | 15-20% of license cost | None |
| **Druva** | Standard / Premium / Elite | 24/7 for all paid tiers | Bundled in higher tiers | $10M data resilience |
| **AvePoint** | Standard / Premium | Not public | Bundled | $1M data resilience |
| **Rubrik** | Standard / Enterprise + CEM | Requires CEM subscription | CEM = extra cost | Data protection warranty (requires CEM) |

### Key Patterns

1. **Every competitor charges extra for premium support** — 15-20% of license, or a separate subscription
2. **Sev-1 24/7 is standard** at Production tier and above — customers expect this
3. **Data resilience guarantees** ($1M-$10M) are becoming a competitive differentiator
4. **Dedicated account managers** (SAM/CEM) are reserved for enterprise customers
5. **Community/free tier support** is best-effort email only — no SLA

### What Competitors Get Wrong

- Veeam forum complaints about slow response times and "support quality lacking"
- Rubrik locks warranty behind CEM subscription — feels like a tax
- Druva's credit-based pricing confuses support cost allocation
- None offer in-product AI support or self-service troubleshooting from backup data

---

## 2. KavachIQ Support Strategy

### Philosophy

**"The best support ticket is the one that never gets filed."**

Our product already has built-in diagnostics, health scoring, error codes with fix suggestions, and pre-flight checks. The support strategy builds on this foundation:

1. **Self-service first** — AI chatbot + knowledge base resolves 50%+ of questions
2. **Product-guided resolution** — Error codes (E1xxx-E7xxx) include fix steps, correlation IDs for instant debugging
3. **Human escalation** — When self-service fails, fast human response
4. **Proactive monitoring** — We detect issues before customers notice them

### Support Tiers by Pricing Plan

| Capability | Community (Free) | Professional ($1.50) | Business ($3.00) | Enterprise ($5.00) |
|-----------|-----------------|---------------------|------------------|-------------------|
| **Knowledge base + docs** | Yes | Yes | Yes | Yes |
| **AI chatbot (self-service)** | Yes | Yes | Yes | Yes |
| **Community forum** | Yes | Yes | Yes | Yes |
| **Error codes with fix steps** | Yes (product built-in) | Yes | Yes | Yes |
| **Diagnostics dashboard** | Yes (product built-in) | Yes | Yes | Yes |
| **Email support** | Best-effort | 24h SLA | 8h SLA | 4h SLA |
| **Chat support** | No | Business hours | Business hours | 24/7 |
| **Phone support** | No | No | Sev-1 only | 24/7 |
| **Sev-1 response** | N/A | 24h | 4h | 1h |
| **Sev-2 response** | N/A | 48h | 8h | 4h |
| **Dedicated account manager** | No | No | No | Yes |
| **Onboarding assistance** | Self-service | Self-service + docs | Guided (1 session) | White-glove |
| **Quarterly health review** | No | No | No | Yes |
| **Data resilience guarantee** | No | No | No | $1M |

---

## 3. Support Tooling & Cost Model

### Phase 1: Bootstrap (0-20 customers) — $0-200/mo

| Tool | Purpose | Cost |
|------|---------|------|
| **GitHub Discussions** | Community forum + feature requests | $0 (free) |
| **Linear / GitHub Issues** | Internal ticket tracking | $0 (free tier) |
| **Email (support@kavachiq.com)** | Primary support channel | $0 (Google Workspace) |
| **Docs site (built-in /docs)** | Knowledge base — already built | $0 |
| **AI chatbot (Chatbase/Docsie)** | Self-service from knowledge base | $0-49/mo |
| **Founder inbox** | All tickets go to founder initially | $0 |
| **Total** | | **~$50/mo** |

**Why this works at 0-20 customers:**
- Volume: ~2-5 tickets/week (most issues resolved by error codes + docs)
- Founder handles all tickets — builds deep understanding of customer pain
- AI chatbot deflects 30-50% of routine questions
- Product's built-in diagnostics prevent most issues from becoming tickets

### Phase 2: Growth (20-100 customers) — $500-1,500/mo

| Tool | Purpose | Cost |
|------|---------|------|
| **Intercom Essential** | Chat + email + AI (Fin) | $39/seat × 2 = $78/mo |
| **Intercom Fin AI** | AI resolution | ~$100-300/mo (at $0.99/resolution) |
| **Knowledge base (Intercom)** | Self-service articles | Included |
| **Status page (Instatus)** | Public uptime transparency | $20/mo |
| **0.5 FTE support hire** | Part-time support engineer | $3,000/mo |
| **Total** | | **~$3,500/mo** |

**Why this works at 20-100 customers:**
- Volume: ~20-50 tickets/week
- Fin AI resolves 40-60% automatically
- 0.5 FTE handles escalations + complex issues
- Intercom provides chat, email, and knowledge base in one tool

### Phase 3: Scale (100-500 customers) — $5,000-15,000/mo

| Tool | Purpose | Cost |
|------|---------|------|
| **Intercom Advanced** | Full platform + workflows | $99/seat × 3 = $297/mo |
| **Intercom Fin AI** | AI resolution at scale | ~$500-1,000/mo |
| **Status page (Instatus Pro)** | Component-level status | $50/mo |
| **PagerDuty** | On-call rotation for Sev-1 | $25/user × 3 = $75/mo |
| **2 FTE support engineers** | Dedicated support team | $12,000/mo |
| **Total** | | **~$13,000/mo** |

---

## 4. Cost Impact on Pricing & Margins

### Support Cost Per Customer

| Phase | Customers | Monthly Support Cost | Cost/Customer | % of ARPU (Pro $1.50 × 100 users) |
|-------|-----------|---------------------|---------------|-----------------------------------|
| Bootstrap (0-20) | 10 | $50 | $5/customer | 3% |
| Growth (20-100) | 50 | $3,500 | $70/customer | 47% |
| Scale (100-500) | 200 | $13,000 | $65/customer | 43% |

### Support Cost Per User

| Phase | Users | Monthly Support Cost | Cost/User |
|-------|-------|---------------------|-----------|
| Bootstrap | 1,000 | $50 | $0.05 |
| Growth | 5,000 | $3,500 | $0.70 |
| Scale | 20,000 | $13,000 | $0.65 |

### Updated Margin Analysis (Including Support)

#### Phase 1: Bootstrap (10 customers, 1,000 users)

| Line Item | Monthly |
|-----------|---------|
| Revenue (1,000 users × $2.50 avg) | $2,500 |
| Infrastructure | $445 |
| Support | $50 |
| **Total cost** | **$495** |
| **Gross margin** | **$2,005 (80%)** |

#### Phase 2: Growth (50 customers, 5,000 users)

| Line Item | Monthly |
|-----------|---------|
| Revenue (5,000 users × $2.50 avg) | $12,500 |
| Infrastructure | $445 |
| Support (0.5 FTE + tools) | $3,500 |
| **Total cost** | **$3,945** |
| **Gross margin** | **$8,555 (68%)** |

#### Phase 3: Scale (200 customers, 20,000 users)

| Line Item | Monthly |
|-----------|---------|
| Revenue (20,000 users × $2.50 avg) | $50,000 |
| Infrastructure | $1,500 |
| Support (2 FTE + tools) | $13,000 |
| **Total cost** | **$14,500** |
| **Gross margin** | **$35,500 (71%)** |

### Key Insight

**Support is the dominant cost, not infrastructure.** At growth stage, support is 89% of total costs ($3,500 vs $445 infra). This is typical for SaaS — the question is how to keep support cost per user declining as you scale.

---

## 5. Cost Reduction Strategies

### Strategy 1: AI-First Self-Service (Target: 50% ticket deflection)

| Investment | Impact | ROI |
|-----------|--------|-----|
| AI chatbot trained on our docs + error codes | Deflects 50% of routine questions | Save ~$1,750/mo at growth stage |
| In-product error codes with fix steps | Customer self-resolves without filing ticket | Already built (E1xxx-E7xxx) |
| Diagnostics dashboard | Admin sees exactly what's wrong | Already built (/api/diagnostics) |
| Health scoring + anomaly alerts | Proactive — customer warned before they notice | Already built (Smart Engine) |

**Our product advantage:** Most support tools add AI on top. Our error codes, diagnostics, and health scoring are **built into the product** — reducing tickets before they're created.

### Strategy 2: Community-Powered Support

| Channel | Cost | Impact |
|---------|------|--------|
| GitHub Discussions | Free | Power users answer each other's questions |
| Community Slack/Discord | Free | Real-time peer support |
| Monthly office hours (Zoom) | Free | Founder Q&A builds trust, identifies patterns |

### Strategy 3: Proactive Monitoring (Reduce Sev-1 Incidents)

| Mechanism | Already Built? | Impact |
|-----------|---------------|--------|
| Circuit breaker alerts | Yes | Notifies admin when tenant API is failing |
| Pre-flight checks | Yes | Blocks operations that would fail |
| Anomaly detection | Yes | Detects ransomware/breaches early |
| Health score degradation | Yes | Warns before SLA violations |
| Stale job detection | Yes | Auto-requeues stuck jobs |

**Estimated impact:** 30-40% fewer Sev-1 tickets because the product self-heals or warns before failure.

### Strategy 4: Support as Revenue (Enterprise Tier)

| Offering | Price | Margin |
|---------|-------|--------|
| White-glove onboarding | Included in Enterprise ($5/user) | Absorbed |
| Dedicated account manager | Included in Enterprise | Absorbed |
| Quarterly health reviews | Included in Enterprise | Builds retention |
| Custom SLA (99.9% uptime) | Enterprise only | Differentiator |
| Data resilience guarantee ($1M) | Enterprise only | Marketing tool (rarely claimed) |

Enterprise tier at $5/user includes everything — customer never feels nickel-and-dimed. This is the opposite of Veeam (15-20% surcharge) and Rubrik (CEM subscription).

---

## 6. Comparison: KavachIQ vs Competitors on Support

| Capability | KavachIQ | Veeam | Druva | Rubrik |
|-----------|----------|-------|-------|--------|
| AI self-service chatbot | Included (all tiers) | No | No | No |
| In-product error codes with fix steps | Yes (E1xxx-E7xxx) | No | No | No |
| Built-in diagnostics dashboard | Yes (/diagnostics) | No | Basic | No |
| Proactive health monitoring | Yes (Smart Engine) | No | Limited | No |
| Community support | GitHub Discussions | Forums | Community | Community |
| Email SLA (Professional) | 24 hours | 24 hours (Basic) | Varies | Varies |
| Premium support surcharge | $0 (included at tier) | 15-20% of license | Tier-dependent | CEM subscription |
| Data resilience guarantee | $1M (Enterprise) | None | $10M (Elite) | Warranty (requires CEM) |
| Dedicated account manager | Enterprise ($5/user) | Premier only | Elite only | Enterprise + CEM |

**Our advantage:** Support intelligence is **built into the product**, not layered on as a separate cost. Error codes tell customers exactly what's wrong and how to fix it. Diagnostics show system health in real-time. Most competitors make you file a ticket and wait.

---

## 7. SLA Framework

### Severity Definitions

| Severity | Definition | Example |
|----------|-----------|---------|
| **Sev-1 (Critical)** | Platform down, no backup/restore possible, data at risk | Circuit breaker open, storage failure, encryption error |
| **Sev-2 (High)** | Significant feature degraded, workaround available | Single workload backup failing, slow performance |
| **Sev-3 (Medium)** | Minor feature issue, no data risk | UI bug, report incorrect, non-critical alert |
| **Sev-4 (Low)** | Question, feature request, documentation | "How do I configure WORM?" |

### Response Time SLA

| Severity | Community | Professional | Business | Enterprise |
|----------|-----------|-------------|----------|-----------|
| Sev-1 | Best effort | 24h | 4h | 1h |
| Sev-2 | Best effort | 48h | 8h | 4h |
| Sev-3 | Best effort | 72h | 24h | 8h |
| Sev-4 | Best effort | 5 business days | 48h | 24h |

### Resolution Time Targets

| Severity | Target | Escalation |
|----------|--------|-----------|
| Sev-1 | 4 hours | Immediate founder/CTO involvement |
| Sev-2 | 24 hours | Senior engineer within 2 hours |
| Sev-3 | 5 business days | Standard queue |
| Sev-4 | 10 business days | Backlog |

---

## 8. Implementation Timeline

| Phase | When | Key Actions |
|-------|------|-------------|
| **Now** | Week 1 | Set up support@kavachiq.com, GitHub Discussions, write top 20 KB articles |
| **Month 1** | With first customers | Founder handles all tickets, document common issues, refine error codes |
| **Month 3** | At 10+ customers | Deploy AI chatbot on docs, add status page, measure ticket volume |
| **Month 6** | At 30+ customers | Evaluate Intercom vs Zendesk, hire first support engineer (part-time) |
| **Month 12** | At 100+ customers | Full Intercom deployment, Fin AI, 1 FTE support, PagerDuty for on-call |

### Week 1 Knowledge Base Articles (Top 20)

| # | Article | Deflects |
|---|---------|----------|
| 1 | Getting started: Connect your M365 tenant | Onboarding questions |
| 2 | Error E1001: Connector not configured | Config issues |
| 3 | Error E1002: Invalid client secret | Auth failures |
| 4 | Error E2001: Invalid credentials | Login issues |
| 5 | Understanding your recovery confidence score | Feature questions |
| 6 | How SLA policies and retention work | Policy confusion |
| 7 | Reading the diagnostics health check | Admin troubleshooting |
| 8 | What does the circuit breaker do? | System behavior |
| 9 | How criticality scoring works | Intelligence questions |
| 10 | Restoring a single email or file | Restore how-to |
| 11 | Understanding RPO/RTO compliance | Compliance questions |
| 12 | Setting up WORM immutable storage | Enterprise feature |
| 13 | Teams chat backup: what's included | Coverage questions |
| 14 | Entra ID backup: object types covered | Coverage questions |
| 15 | Troubleshooting Graph API throttling (E3001) | Performance issues |
| 16 | How to run a test restore | Verification |
| 17 | Reading the anomaly detection alerts | Alert fatigue |
| 18 | Bulk backup: using backup-all with idempotency | API usage |
| 19 | HIPAA compliance with KavachIQ | Compliance mapping |
| 20 | SOC 2 compliance with KavachIQ | Compliance mapping |

---

## 9. Metrics to Track

| Metric | Bootstrap Target | Growth Target | Scale Target |
|--------|-----------------|---------------|-------------|
| First response time | < 24h | < 8h | < 4h |
| Resolution time (median) | < 48h | < 24h | < 12h |
| Ticket volume / customer / month | < 1 | < 0.5 | < 0.3 |
| AI deflection rate | 30% | 50% | 60% |
| Customer satisfaction (CSAT) | > 85% | > 90% | > 92% |
| NPS | > 40 | > 50 | > 60 |
| Support cost / user / month | $0.05 | $0.70 | $0.65 |
| Support cost as % of ARR | 2% | 8% | 6% |

---

## Sources

- [Veeam Customer Support Policy](https://www.veeam.com/legal/support-policy.html)
- [Druva Customer Success](https://www.druva.com/support)
- [SaaS Support Cost Benchmarks](https://livechatai.com/blog/customer-support-cost-benchmarks)
- [SaaS Spending Benchmarks 2025 (SaaS Capital)](https://www.saas-capital.com/blog-posts/spending-benchmarks-for-private-b2b-saas-companies/)
- [Intercom vs Zendesk 2026 Comparison](https://www.freqens.com/blog/intercom-vs-zendesk-pricing-features-and-best-use-cases-2026)
- [AI Customer Support ROI Benchmarks 2026](https://www.gleap.io/blog/ai-chatbot-roi-benchmarks-saas)
- [Knowledge Base Chatbot 2026](https://www.docsie.io/blog/articles/knowledge-base-chatbot-2026/)
- [Data Resiliency Guarantees (TechTarget)](https://www.techtarget.com/searchdisasterrecovery/news/252527632/Data-resiliency-guarantees-offer-new-kind-of-assurance)
