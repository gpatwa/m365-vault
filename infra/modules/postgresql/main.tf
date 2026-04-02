# PostgreSQL as a Container App — avoids Flexible Server quota restrictions
# Uses Azure Container Apps with a persistent Azure Files volume for data

resource "azurerm_storage_share" "pgdata" {
  name               = "pgdata-${var.environment}"
  storage_account_name = var.storage_account_name
  quota              = 5 # GB
}

resource "azurerm_container_app" "postgres" {
  name                         = "postgres-${var.environment}"
  container_app_environment_id = var.container_app_environment_id
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
        value = var.database_name
      }
      env {
        name  = "POSTGRES_USER"
        value = var.admin_username
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
      storage_name = "pgdata-${var.environment}"
      storage_type = "AzureFile"
    }
  }

  secret {
    name  = "db-password"
    value = var.admin_password
  }

  ingress {
    external_traffic = false
    target_port      = 5432
    transport        = "tcp"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = var.tags
}
