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

  template {
    min_replicas = var.backend_min_replicas
    max_replicas = var.backend_max_replicas

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
        value = var.cors_origins
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
    external_enabled = false
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
    min_replicas = 1
    max_replicas = 3

    container {
      name   = "frontend"
      image  = "${var.acr_login_server}/m365vault-frontend:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"
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

# Grant backend managed identity access to Key Vault secrets
resource "azurerm_role_assignment" "backend_keyvault" {
  count                = var.keyvault_id != "" ? 1 : 0
  scope                = var.keyvault_id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.backend.identity[0].principal_id
}
