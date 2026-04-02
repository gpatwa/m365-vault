output "connection_string" {
  value     = "postgresql+asyncpg://${var.admin_username}:${var.admin_password}@postgres-${var.environment}:5432/${var.database_name}"
  sensitive = true
}

output "fqdn" {
  value = "postgres-${var.environment}"
}

output "server_name" {
  value = azurerm_container_app.postgres.name
}

output "id" {
  value = azurerm_container_app.postgres.id
}
