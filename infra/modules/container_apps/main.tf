resource "azurerm_log_analytics_workspace" "this" {
  name                = "log-m365vault-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

resource "azurerm_container_app_environment" "this" {
  name                       = "cae-m365vault-${var.environment}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id

  tags = var.tags
}

# ── Storage for PostgreSQL data persistence ──────────────────────────

resource "azurerm_container_app_environment_storage" "pgdata" {
  name                         = "pgdata"
  container_app_environment_id = azurerm_container_app_environment.this.id
  account_name                 = var.storage_account_name
  share_name                   = "pgdata-${var.environment}"
  access_key                   = var.storage_account_key
  access_mode                  = "ReadWrite"
}

resource "azurerm_storage_share" "pgdata" {
  name               = "pgdata-${var.environment}"
  storage_account_name = var.storage_account_name
  quota              = 5
}

# ── PostgreSQL Container App ─────────────────────────────────────────

resource "azurerm_container_app" "postgres" {
  name                         = "postgres-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  template {
    min_replicas = 1
    max_replicas = 1

    container {
      name   = "postgres"
      image  = "postgres:16-alpine"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name  = "POSTGRES_DB"
        value = var.db_name
      }
      env {
        name  = "POSTGRES_USER"
        value = var.db_username
      }
      env {
        name        = "POSTGRES_PASSWORD"
        secret_name = "db-password"
      }
      env {
        name  = "PGDATA"
        value = "/var/lib/postgresql/data/pgdata"
      }

      volume_mounts {
        name = "pgdata"
        path = "/var/lib/postgresql/data"
      }
    }

    volume {
      name         = "pgdata"
      storage_name = azurerm_container_app_environment_storage.pgdata.name
      storage_type = "AzureFile"
    }
  }

  secret {
    name  = "db-password"
    value = var.db_password
  }

  ingress {
    target_port = 5432
    transport   = "tcp"
    exposed_port = 5432

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = var.tags
}

# ── Backend Container App ────────────────────────────────────────────

resource "azurerm_container_app" "backend" {
  name                         = "m365vault-backend-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server               = var.acr_login_server
    username             = var.acr_admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = var.acr_admin_password
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }

  secret {
    name  = "secret-key"
    value = var.app_secret_key
  }

  secret {
    name  = "encryption-master-key"
    value = var.encryption_master_key
  }

  secret {
    name  = "azure-storage-connection-string"
    value = var.storage_connection_string
  }

  secret {
    name  = "redis-url"
    value = var.redis_url
  }

  # ── App secrets from Key Vault (pushed via make secrets-push) ────
  # These use Key Vault references — secret values never in Terraform state.
  # If Key Vault URI not set (first deploy), fall back to placeholder.
  dynamic "secret" {
    for_each = var.keyvault_uri != "" ? ["stripe-secret-key", "stripe-webhook-secret", "resend-api-key", "connector-app-secret"] : []
    content {
      name                = secret.value
      key_vault_secret_id = "${trimsuffix(var.keyvault_uri, "/")}secrets/${secret.value}"
      identity            = "System"
    }
  }
  # Fallback for first deploy (before Key Vault exists)
  dynamic "secret" {
    for_each = var.keyvault_uri == "" ? ["stripe-secret-key", "stripe-webhook-secret", "resend-api-key", "connector-app-secret"] : []
    content {
      name  = secret.value
      value = "not-configured"
    }
  }

  template {
    min_replicas = var.backend_min_replicas
    max_replicas = var.backend_max_replicas

    # Autoscale: scale up when concurrent HTTP requests exceed 10
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "10"
    }

    container {
      name   = "backend"
      image  = "${var.acr_login_server}/m365vault-backend:${var.image_tag}"
      cpu    = var.backend_cpu
      memory = var.backend_memory

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "azure"
      }
      env {
        name        = "AZURE_STORAGE_CONNECTION_STRING"
        secret_name = "azure-storage-connection-string"
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = var.storage_container_name
      }
      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
      env {
        name        = "ENCRYPTION_MASTER_KEY"
        secret_name = "encryption-master-key"
      }
      env {
        name  = "DEBUG"
        value = var.environment == "dev" ? "true" : "false"
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.cors_origins != "" ? var.cors_origins : "*"
      }
      env {
        name  = "DISPATCH_MODE"
        value = "redis"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }

      # ── Stripe Billing ──
      env {
        name        = "STRIPE_SECRET_KEY"
        secret_name = "stripe-secret-key"
      }
      env {
        name        = "STRIPE_WEBHOOK_SECRET"
        secret_name = "stripe-webhook-secret"
      }
      env {
        name  = "STRIPE_PUBLISHABLE_KEY"
        value = var.stripe_publishable_key
      }
      env {
        name  = "STRIPE_PRICE_PROFESSIONAL"
        value = var.stripe_price_professional
      }
      env {
        name  = "STRIPE_PRICE_BUSINESS"
        value = var.stripe_price_business
      }
      env {
        name  = "STRIPE_PRICE_ENTERPRISE"
        value = var.stripe_price_enterprise
      }

      # ── Email (Resend) ──
      env {
        name        = "RESEND_API_KEY"
        secret_name = "resend-api-key"
      }
      env {
        name  = "EMAIL_PROVIDER"
        value = var.email_provider
      }
      env {
        name  = "FRONTEND_URL"
        value = var.frontend_url
      }

      # ── Microsoft 365 Connector ──
      env {
        name  = "CONNECTOR_APP_ID"
        value = var.connector_app_id
      }
      env {
        name        = "CONNECTOR_APP_SECRET"
        secret_name = "connector-app-secret"
      }
      env {
        name  = "CONNECTOR_REDIRECT_URI"
        value = var.connector_redirect_uri
      }

      # ── Analytics ──
      env {
        name  = "POSTHOG_API_KEY"
        value = var.posthog_api_key
      }

      liveness_probe {
        path             = "/health"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 10
        interval_seconds = 30
      }

      readiness_probe {
        path             = "/health"
        port             = 8000
        transport        = "HTTP"
        initial_delay    = 5
        interval_seconds = 10
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = var.tags
}

# ── Frontend Container App ───────────────────────────────────────────

resource "azurerm_container_app" "frontend" {
  name                         = "m365vault-frontend-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  registry {
    server               = var.acr_login_server
    username             = var.acr_admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = var.acr_admin_password
  }

  template {
    min_replicas = 0
    max_replicas = 3

    # Autoscale: scale to zero when no HTTP traffic, scale up on requests
    http_scale_rule {
      name                = "http-scaling"
      concurrent_requests = "15"
    }

    container {
      name   = "frontend"
      image  = "${var.acr_login_server}/m365vault-frontend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "BACKEND_URL"
        value = "https://${azurerm_container_app.backend.ingress[0].fqdn}"
      }
    }
  }

  ingress {
    external_enabled = true
    target_port      = 80
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = var.tags
}

# ── Worker Container App ─────────────────────────────────────────────

resource "azurerm_container_app" "worker" {
  name                         = "m365vault-worker-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  registry {
    server               = var.acr_login_server
    username             = var.acr_admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = var.acr_admin_password
  }

  secret {
    name  = "database-url"
    value = var.database_url
  }

  secret {
    name  = "secret-key"
    value = var.app_secret_key
  }

  secret {
    name  = "encryption-master-key"
    value = var.encryption_master_key
  }

  secret {
    name  = "azure-storage-connection-string"
    value = var.storage_connection_string
  }

  secret {
    name  = "redis-url"
    value = var.redis_url
  }

  template {
    min_replicas = var.worker_min_replicas
    max_replicas = var.worker_max_replicas

    # Worker scales to zero when no jobs in queue
    # Scales up when backup/restore jobs are dispatched

    container {
      name    = "worker"
      image   = "${var.acr_login_server}/m365vault-backend:${var.image_tag}"
      cpu     = var.worker_cpu
      memory  = var.worker_memory
      command = ["python", "-m", "app.worker"]

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "STORAGE_BACKEND"
        value = "azure"
      }
      env {
        name        = "AZURE_STORAGE_CONNECTION_STRING"
        secret_name = "azure-storage-connection-string"
      }
      env {
        name  = "AZURE_STORAGE_CONTAINER"
        value = var.storage_container_name
      }
      env {
        name        = "SECRET_KEY"
        secret_name = "secret-key"
      }
      env {
        name        = "ENCRYPTION_MASTER_KEY"
        secret_name = "encryption-master-key"
      }
      env {
        name  = "DISPATCH_MODE"
        value = "redis"
      }
      env {
        name        = "REDIS_URL"
        secret_name = "redis-url"
      }
      env {
        name  = "WORKER_CONCURRENCY"
        value = "3"
      }
    }
  }

  tags = var.tags
}

# Grant backend + worker managed identity access to Key Vault secrets
resource "azurerm_role_assignment" "backend_keyvault" {
  count                = var.enable_keyvault ? 1 : 0
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.backend.identity[0].principal_id
}

resource "azurerm_role_assignment" "worker_keyvault" {
  count                = var.enable_keyvault ? 1 : 0
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.worker.identity[0].principal_id
}
