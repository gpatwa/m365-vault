# Azure Database for PostgreSQL — Flexible Server
# Persistent, managed, auto-backup, no chmod issues.
#
# Replaces the Container App-based PostgreSQL which used ephemeral storage.
# B1ms tier: 1 vCore, 2 GB RAM, 32 GB storage — ~$13/mo

resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "pg-kavachiq-${var.environment}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "16"
  administrator_login           = var.admin_username
  administrator_password        = var.admin_password
  sku_name                      = var.sku_name
  storage_mb                    = var.storage_mb
  backup_retention_days         = 7
  geo_redundant_backup_enabled  = false
  zone                          = "1"

  # Allow Azure services (Container Apps) to connect
  public_network_access_enabled = true

  tags = var.tags
}

# Firewall rule: allow Azure services
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "allow-azure-services"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Create the application database
resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}
