output "connection_string" {
  value     = azurerm_storage_account.this.primary_connection_string
  sensitive = true
}

output "account_name" {
  value = azurerm_storage_account.this.name
}

output "container_name" {
  value = azurerm_storage_container.backups.name
}

output "id" {
  value = azurerm_storage_account.this.id
}

output "primary_access_key" {
  value     = azurerm_storage_account.this.primary_access_key
  sensitive = true
}
