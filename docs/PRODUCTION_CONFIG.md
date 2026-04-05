# KavachIQ Production Configuration

## Domain Setup

| Subdomain | Purpose | DNS Record |
|---|---|---|
| `kavachiq.com` | Landing page | CNAME → Azure frontend |
| `app.kavachiq.com` | Dashboard / App | CNAME → Azure frontend Container App |
| `api.kavachiq.com` | Backend API | CNAME → Azure backend Container App |

### Cloudflare DNS Records

```
Type    Name    Content                                                          Proxy
CNAME   @       m365vault-frontend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io   Proxied
CNAME   app     m365vault-frontend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io   Proxied
CNAME   api     m365vault-backend-dev.mangodesert-7599c248.centralus.azurecontainerapps.io    Proxied
```

### Azure Custom Domain Setup

```bash
# Add custom domains to Container Apps
az containerapp hostname add --name m365vault-frontend-dev --resource-group rg-m365vault-dev --hostname app.kavachiq.com
az containerapp hostname add --name m365vault-frontend-dev --resource-group rg-m365vault-dev --hostname kavachiq.com
az containerapp hostname add --name m365vault-backend-dev --resource-group rg-m365vault-dev --hostname api.kavachiq.com

# Bind managed SSL certificates
az containerapp hostname bind --name m365vault-frontend-dev --resource-group rg-m365vault-dev --hostname app.kavachiq.com --environment cae-m365vault-dev --validation-method CNAME
az containerapp hostname bind --name m365vault-backend-dev --resource-group rg-m365vault-dev --hostname api.kavachiq.com --environment cae-m365vault-dev --validation-method CNAME
```

---

## Environment Variables (Production)

### Critical Security

```bash
SECRET_KEY=<openssl rand -hex 32>
ENCRYPTION_MASTER_KEY=<openssl rand -hex 32>
FORCE_HTTPS=true
DEBUG=false
DEMO_MODE=false
LICENSE_TIER=community
CORS_ORIGINS=https://kavachiq.com,https://app.kavachiq.com
```

### Email (Resend)

```bash
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxx
EMAIL_FROM="KavachIQ <noreply@kavachiq.com>"
FRONTEND_URL=https://app.kavachiq.com
```

#### Resend Domain Verification
1. Go to https://resend.com/domains → Add domain → `kavachiq.com`
2. Add DNS records in Cloudflare:
   - SPF: `TXT` record on `@` → `v=spf1 include:_spf.resend.com ~all`
   - DKIM: `CNAME` record → provided by Resend
   - DMARC: `TXT` on `_dmarc` → `v=DMARC1; p=none;`

### Stripe

```bash
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxx
STRIPE_PRICE_PROFESSIONAL=price_xxxxxxxxxxxx
STRIPE_PRICE_BUSINESS=price_xxxxxxxxxxxx
STRIPE_PRICE_ENTERPRISE=price_xxxxxxxxxxxx
```

#### Stripe Webhook
Update webhook endpoint in Stripe Dashboard:
`https://api.kavachiq.com/api/billing/webhook`

### Microsoft OAuth

```bash
CONNECTOR_APP_ID=d5c6ca1d-0f4a-4e14-a121-136fde89512d
CONNECTOR_APP_SECRET=<from Azure Key Vault>
CONNECTOR_REDIRECT_URI=https://app.kavachiq.com/onboard/callback
```

#### Update Azure App Registration
1. Go to Azure Portal → App Registrations → KavachIQ Connector
2. Authentication → Add redirect URI: `https://app.kavachiq.com/onboard/callback`
3. Remove old: `https://m365vault-frontend-dev.happyflower-*.azurecontainerapps.io/onboard/callback`

### Analytics

```bash
# PostHog (already configured in config.js)
# Only activates on non-localhost domains
```

### Database

```bash
DATABASE_URL=postgresql+asyncpg://m365vault:M365vault_Dev2026!@pgm365vault-dev.postgres.database.azure.com:5432/m365vault?ssl=require
```

---

## Checklist Before Go-Live

- [ ] Domain registered: kavachiq.com
- [ ] DNS CNAME records added in Cloudflare
- [ ] Azure Custom Domain configured for frontend + backend
- [ ] SSL certificates bound (managed by Azure)
- [ ] SECRET_KEY regenerated (not dev value)
- [ ] ENCRYPTION_MASTER_KEY regenerated (not dev value)
- [ ] FORCE_HTTPS=true
- [ ] CORS_ORIGINS set to kavachiq.com
- [ ] EMAIL_PROVIDER=resend with API key
- [ ] Resend domain verified (SPF + DKIM + DMARC)
- [ ] Stripe webhook URL updated to api.kavachiq.com
- [ ] Stripe webhook secret configured
- [ ] Microsoft OAuth redirect URI updated
- [ ] LICENSE_TIER=community (users start free)
- [ ] DEMO_MODE=false
- [ ] DEBUG=false
- [ ] PostHog tracking verified on production domain
- [ ] Test: registration → email received → verify → login → billing → checkout
