output "connection_string" {
  value     = "postgresql+asyncpg://${var.admin_username}:${var.admin_password}@${azurerm_postgresql_flexible_server.this.fqdn}:5432/${var.database_name}?ssl=require"
  sensitive = true
}

output "fqdn" {
  value = azurerm_postgresql_flexible_server.this.fqdn
}

output "server_name" {
  value = azurerm_postgresql_flexible_server.this.name
}

output "id" {
  value = azurerm_postgresql_flexible_server.this.id
}
