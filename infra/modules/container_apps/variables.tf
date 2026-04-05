variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "acr_login_server" {
  type = string
}

variable "acr_admin_username" {
  type = string
}

variable "acr_admin_password" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "db_password" {
  type      = string
  sensitive = true
  default   = ""
}

variable "db_username" {
  type    = string
  default = "m365vault_admin"
}

variable "db_name" {
  type    = string
  default = "m365vault"
}

variable "storage_account_name" {
  type    = string
  default = ""
}

variable "storage_account_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "app_secret_key" {
  type      = string
  sensitive = true
}

variable "encryption_master_key" {
  type      = string
  sensitive = true
}

variable "storage_connection_string" {
  type      = string
  sensitive = true
}

variable "storage_container_name" {
  type    = string
  default = "m365vault-backups"
}

variable "cors_origins" {
  type    = string
  default = ""
}

variable "keyvault_id" {
  type    = string
  default = ""
}

variable "enable_keyvault" {
  description = "Whether Key Vault integration is enabled (avoids count depending on unknown values)"
  type        = bool
  default     = true
}

variable "backend_cpu" {
  type    = number
  default = 0.5
}

variable "backend_memory" {
  type    = string
  default = "1Gi"
}

variable "backend_min_replicas" {
  type    = number
  default = 1
}

variable "backend_max_replicas" {
  type    = number
  default = 3
}

variable "redis_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "worker_cpu" {
  type    = number
  default = 0.5
}

variable "worker_memory" {
  type    = string
  default = "1Gi"
}

variable "worker_min_replicas" {
  type    = number
  default = 1
}

variable "worker_max_replicas" {
  type    = number
  default = 3
}

variable "tags" {
  type    = map(string)
  default = {}
}

# ── Stripe Billing ──────────────────────────────────────────────────
variable "stripe_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "stripe_webhook_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "stripe_publishable_key" {
  type    = string
  default = ""
}

variable "stripe_price_professional" {
  type    = string
  default = ""
}

variable "stripe_price_business" {
  type    = string
  default = ""
}

variable "stripe_price_enterprise" {
  type    = string
  default = ""
}

# ── Email (Resend) ──────────────────────────────────────────────────
variable "resend_api_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "email_provider" {
  type    = string
  default = "resend"
}

variable "frontend_url" {
  type    = string
  default = "https://app.kavachiq.com"
}

# ── Microsoft 365 Connector ─────────────────────────────────────────
variable "connector_app_id" {
  type    = string
  default = ""
}

variable "connector_app_secret" {
  type      = string
  sensitive = true
  default   = ""
}

variable "connector_redirect_uri" {
  type    = string
  default = "https://app.kavachiq.com/onboard/callback"
}

# ── PostHog Analytics ───────────────────────────────────────────────
variable "posthog_api_key" {
  type    = string
  default = ""
}
