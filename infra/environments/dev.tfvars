environment           = "dev"
location              = "centralus"

# ACR
acr_sku               = "Basic"

# PostgreSQL — Burstable for dev
postgresql_sku        = "B_Standard_B1ms"
postgresql_storage_mb = 32768

# Storage — locally redundant for dev
storage_redundancy    = "LRS"

# Container Apps — small for dev
backend_cpu           = 0.5
backend_memory        = "1Gi"
backend_min_replicas  = 1
backend_max_replicas  = 3

# Worker — scale-to-zero when idle, KEDA scales on Redis queue depth (saves ~$15/mo)
worker_cpu              = 0.5
worker_memory           = "1Gi"
worker_min_replicas     = 0
worker_max_replicas     = 5
worker_concurrency      = "3"
worker_scale_threshold  = "5"

# Redis — Basic C0 for dev (~$16/mo)
redis_sku             = "Basic"
redis_capacity        = 0
redis_family          = "C"

# ── Stripe, Resend, M365 Connector ──────────────────────────────────
# Sensitive values passed via TF_VAR_* environment variables or -var flags:
#   TF_VAR_stripe_secret_key, TF_VAR_stripe_webhook_secret,
#   TF_VAR_resend_api_key, TF_VAR_connector_app_id,
#   TF_VAR_connector_app_secret
#
# Non-sensitive values:
backend_custom_domain     = "api.kavachiq.com"
cors_origins              = "https://kavachiq.com,https://app.kavachiq.com"
email_provider            = "resend"
frontend_url              = "https://kavachiq.com"
connector_redirect_uri    = "https://kavachiq.com/onboard/callback"
