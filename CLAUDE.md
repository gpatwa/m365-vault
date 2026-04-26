# KavachIQ — Development Notes

# CLAUDE.md

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a staff or principal engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.


## Docker Build Platform

**IMPORTANT**: This project deploys to Azure Container Apps which requires `linux/amd64` images.
When building Docker images on Apple Silicon (M1/M2/M3) Macs, always use:

```bash
docker build --platform linux/amd64 -t <tag> .
```

The Makefile `build` and `acr-push` targets already include `--platform linux/amd64`.
The `docker-compose.yml` also sets `platform: linux/amd64` on backend and frontend services.

### Quick Reference

| Command | Purpose |
|---|---|
| `make dev` | Start local dev stack (Docker Compose: PG + backend + frontend) |
| `make test-backend` | Run backend tests against SQLite (fast, no Docker) |
| `make test-pg` | Run backend tests against Docker PostgreSQL (catches migration bugs) |
| `make build` | Build images (linux/amd64) |
| `make safe-deploy ENV=dev` | Build → push → health check → E2E sanity (65 tests) |
| `make release` | Full pipeline: test-local → test-pg → safe-deploy → e2e-test |
| `make e2e-test` | Run E2E certification against live environment |
| `make acr-push` | Build + push to Azure Container Registry |
| `make tf-apply` | Deploy infrastructure |
| `make az-status` | Check Azure resource status |
| `make az-cleanup` | Full Azure teardown + state reset |
| `make bootstrap` | One-time Azure + GitHub setup |

## Azure Dev Environment — Dormant Mode (cost-optimized)

The dev Azure environment is intentionally **stripped to the data plane** to minimize idle cost (~$22/month vs ~$81/month with full stack). Marketing (`kavachiq.com` on Cloudflare Pages) is unaffected.

### What's deleted vs kept

**Deleted** (rebuildable via terraform + safe-deploy):
- Container Apps environment `cae-m365vault-dev`
- 3 container apps: `m365vault-backend-dev`, `m365vault-worker-dev`, `m365vault-frontend-dev`
- PostgreSQL Flexible Server `pg-kavachiq-dev` (data lost — fresh DB on rebuild)

**Kept** (data plane + always-on minimums):
- Redis `redis-m365vault-dev` (Basic C0, ~$16/mo — Basic tier can't be stopped)
- ACR `acrm365vaultdev` (Basic, ~$5/mo — image registry)
- Storage Account `stm365vaultdev` (snapshot blobs from prior runs, if any)
- Key Vault `kv-m365vault-dev` (secrets)
- Log Analytics `log-m365vault-dev` (under free tier)

### Side effects of dormant mode

- `app.kavachiq.com` returns an error (no Azure backend). Marketing Sign In button on `kavachiq.com` will route to a broken URL until cold-wake. Acceptable for pre-customer phase.
- `api.kavachiq.com` returns an error.
- Marketing site `kavachiq.com` (Cloudflare Pages) **stays up**.
- All `docs/sales/` assets, scenarios, security page, etc. remain live.

### Cold-wake runbook (~30–60 minutes)

When you need to bring the dev app back for a demo or evaluation:

```bash
# 1. Recreate infrastructure (Container Apps env + apps + Postgres) via terraform
make tf-apply ENV=dev   # ~10 min

# 2. Build + push images, then deploy revisions
make safe-deploy ENV=dev   # ~15 min

# 3. Run database migrations on the fresh Postgres
make db-migrate ENV=dev   # ~2 min

# 4. (Manual, Azure portal) Re-bind custom domains — these are NOT in terraform:
#    Container Apps → m365vault-backend-dev → Custom domains → add api.kavachiq.com
#    Container Apps → m365vault-frontend-dev → Custom domains → add app.kavachiq.com
#    Each binding waits 5–15 min for managed cert issuance.
#    Cloudflare DNS CNAMEs already point to the Azure FQDNs — no DNS changes needed.

# 5. Verify
curl -sI https://api.kavachiq.com/health
curl -sI https://app.kavachiq.com/
```

### Re-dormant runbook (~5 minutes)

When done with the demo:

```bash
az containerapp delete -n m365vault-backend-dev  -g rg-m365vault-dev --yes
az containerapp delete -n m365vault-worker-dev   -g rg-m365vault-dev --yes
az containerapp delete -n m365vault-frontend-dev -g rg-m365vault-dev --yes
az containerapp env delete -n cae-m365vault-dev  -g rg-m365vault-dev --yes
az postgres flexible-server delete -n pg-kavachiq-dev -g rg-m365vault-dev --yes
```

### Why dormant instead of stop/start

PostgreSQL Flexible Server **auto-restarts after 7 days** of being stopped, which cascades into backend container scale-up + worker scale-up + cost climb. Deleting the Container Apps env breaks the cascade permanently. Deleting Postgres removes the auto-restart timer entirely.

## CDN Caching Strategy (Cloudflare)

The frontend is served through Cloudflare CDN. Cache policy is controlled at the
**origin (nginx)** — Cloudflare respects origin headers. No manual purge needed.

**How it works (nginx.conf.template):**

| Resource | Cache-Control | CDN-Cache-Control | Why |
|---|---|---|---|
| `index.html` (exact) | `no-cache, no-store` | `no-store` | Always fetch fresh HTML |
| SPA routes (`/settings`, etc.) | `no-cache, no-store` | `no-store` | try_files → index.html, same policy |
| `*.js`, `*.css` (hashed) | `public, immutable` | `max-age=31536000` | Filename changes per build, cache forever |

**Key design decisions:**
- `CDN-Cache-Control` header tells Cloudflare specifically what to cache at the edge
- SPA `location /` block sets no-cache (not just `location = /index.html`) because
  `try_files` serves index.html but internal redirects don't inherit headers from other blocks
- Hashed assets use `immutable` — browsers never revalidate, CDN caches for 1 year
- New deploy = new JS filenames → CDN misses → fetches from origin automatically

**Optional: API purge for instant propagation (belt-and-suspenders):**
```bash
export CLOUDFLARE_ZONE_ID="your-zone-id"
export CLOUDFLARE_API_TOKEN="your-api-token"
```
If set, `safe-deploy.sh` purges CDN after health check. Not required — origin headers handle it.

## Marketing Site (Cloudflare Pages)

Marketing pages (`/welcome`, `/about`, `/tour`, `/contact`, `/legal`) are deployed
separately from the app, on Cloudflare Pages. This keeps marketing always-on,
free, and independent of Azure (dev can sleep without taking down the public site).

**Live URL**: https://kavachiq-marketing.pages.dev
**Source**: React components in `frontend/src/pages/{Landing,About,Tour,Contact,Legal}.tsx`

### Update process (manual)

Requires `CLOUDFLARE_API_TOKEN` in `.env.azure` (Cloudflare Pages:Edit permission).

```bash
# 1. Edit the React component(s)
vim frontend/src/pages/Landing.tsx

# 2. Build + prerender + bundle for Cloudflare Pages
cd frontend && npm run build:marketing

# 3. Deploy (sources the token from .env.azure automatically)
make pages-deploy
```

The build runs `tsc` → `vite build` → Puppeteer prerender of 5 pages → bundles
into `frontend/dist-marketing/` → `wrangler pages deploy`. Typical cycle: ~60 seconds.

**What the pipeline does:**
- `npm run build:marketing` → produces `frontend/dist-marketing/` with prerendered
  HTML, Vite assets, `_redirects` (app routes → app.kavachiq.com), robots.txt, sitemap.xml
- `npm run pages:deploy` → `wrangler pages deploy dist-marketing --project-name kavachiq-marketing`

**Verify after deploy:**
```bash
curl -s https://kavachiq-marketing.pages.dev/welcome/ | grep -oE '<title>[^<]+</title>'
```

### Phase 2 (deferred): DNS cutover

When ready to move production traffic, flip DNS:
- `kavachiq.com` → Cloudflare Pages (currently on Azure)
- `app.kavachiq.com` → Azure Container Apps (currently redirects to kavachiq.com)
- `api.kavachiq.com` → unchanged

See `.claude/plans/cozy-painting-popcorn.md` for the full migration plan.

## Architecture

### Domain topology (split-host)

Enterprise SaaS pattern — marketing separated from app for SEO, cost, and deploy cadence:

| Host | Served by | Purpose | Deploy |
|------|-----------|---------|--------|
| `kavachiq.com` | **Cloudflare Pages** | Marketing (static HTML, prerendered) | `make pages-deploy` |
| `app.kavachiq.com` | **Azure Container Apps** | Authenticated React SPA | `make safe-deploy ENV=dev` |
| `api.kavachiq.com` | **Azure Container Apps** | FastAPI backend | `make safe-deploy ENV=dev` |

### Stack

- **Backend**: Python/FastAPI on port 8000
- **Frontend SPA**: React/Vite served by nginx on port 80 (at `app.kavachiq.com`)
- **Marketing site**: Prerendered static HTML on Cloudflare Pages (at `kavachiq.com`)
- **Database**: PostgreSQL 16 (local: Docker, Azure: Flexible Server)
- **Storage**: Local filesystem / MinIO (dev), Azure Blob Storage (prod)
- **Encryption**: AES-256-GCM with per-tenant DEKs wrapped by master KEK
- **Compression**: zstd with content-aware adaptive levels
- **Dedup**: SHA-256 content-addressable with CDC for large files

### Cross-host navigation

Marketing "Sign In" / "Start Free" buttons use the `appUrl()` helper
(`frontend/src/utils/appUrl.ts`) — returns absolute URLs when on `kavachiq.com`,
relative paths on `app.kavachiq.com` and localhost. This gives full-page nav across
hosts while keeping SPA-speed navigation within the app.

CF Pages `_redirects` catches any authenticated route hit on `kavachiq.com` (e.g.
`/dashboard`, `/onboard/callback`) and 301s to the app host. This covers OAuth
callbacks from Microsoft — the redirect URI stays `kavachiq.com/onboard/callback`
but redirects transparently to `app.kavachiq.com/onboard/callback`.

