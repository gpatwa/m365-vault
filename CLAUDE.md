# KavachIQ — Development Notes

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
| `make dev` | Start local dev stack (Docker Compose) |
| `make build` | Build images (linux/amd64) |
| `make acr-push` | Build + push to Azure Container Registry |
| `make tf-apply` | Deploy infrastructure |
| `make az-status` | Check Azure resource status |
| `make az-cleanup` | Full Azure teardown + state reset |
| `make bootstrap` | One-time Azure + GitHub setup |

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

## Architecture

- **Backend**: Python/FastAPI on port 8000
- **Frontend**: React/Vite served by nginx on port 80
- **Database**: PostgreSQL 16 (local: Docker, prod: Azure Flexible Server)
- **Storage**: Local filesystem / MinIO (dev), Azure Blob Storage (prod)
- **Encryption**: AES-256-GCM with per-tenant DEKs wrapped by master KEK
- **Compression**: zstd with content-aware adaptive levels
- **Dedup**: SHA-256 content-addressable with CDC for large files
