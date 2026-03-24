# Shieldio — Development Notes

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

## Architecture

- **Backend**: Python/FastAPI on port 8000
- **Frontend**: React/Vite served by nginx on port 80
- **Database**: PostgreSQL 16 (local: Docker, prod: Azure Flexible Server)
- **Storage**: Local filesystem / MinIO (dev), Azure Blob Storage (prod)
- **Encryption**: AES-256-GCM with per-tenant DEKs wrapped by master KEK
- **Compression**: zstd with content-aware adaptive levels
- **Dedup**: SHA-256 content-addressable with CDC for large files
