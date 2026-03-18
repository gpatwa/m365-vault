output "vault_uri" {
  value = azurerm_key_vault.this.vault_uri
}

output "vault_id" {
  value = azurerm_key_vault.this.id
}

output "secret_key_uri" {
  value = azurerm_key_vault_secret.secret_key.versionless_id
}

output "encryption_master_key_uri" {
  value = azurerm_key_vault_secret.encryption_master_key.versionless_id
}

output "database_url_uri" {
  value = azurerm_key_vault_secret.database_url.versionless_id
}

output "storage_connection_string_uri" {
  value = azurerm_key_vault_secret.storage_connection_string.versionless_id
}
