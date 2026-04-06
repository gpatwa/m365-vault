environment           = "staging"
location              = "centralus"

# ACR — shared with dev (same registry, different image tags)
acr_sku               = "Basic"

# PostgreSQL — same as dev
postgresql_sku        = "B_Standard_B1ms"
postgresql_storage_mb = 32768

# Storage — locally redundant
storage_redundancy    = "LRS"

# Container Apps — minimal (staging scales to zero when idle)
backend_cpu           = 0.25
backend_memory        = "0.5Gi"
backend_min_replicas  = 0
backend_max_replicas  = 2

# Worker — scales to zero
worker_cpu            = 0.25
worker_memory         = "0.5Gi"
worker_min_replicas   = 0
worker_max_replicas   = 1

# Redis — Basic C0 (~$16/mo)
redis_sku             = "Basic"
redis_capacity        = 0
redis_family          = "C"

# ── App Config ──────────────────────────────────────────────────────
# Staging uses same Stripe test keys, Resend sandbox, demo M365 tenant.
# Secrets pushed via: make secrets-push ENV=staging
cors_origins              = "https://app-staging.kavachiq.com,https://staging.kavachiq.com"
email_provider            = "console"
frontend_url              = "https://app-staging.kavachiq.com"
connector_redirect_uri    = "https://app-staging.kavachiq.com/onboard/callback"
