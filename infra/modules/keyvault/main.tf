data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                       = "kv-m365vault-${var.environment}"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = false
  rbac_authorization_enabled = true

  tags = var.tags
}

# Grant the deployer (Terraform) access to manage secrets
resource "azurerm_role_assignment" "deployer_secrets" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Store application secrets
resource "azurerm_key_vault_secret" "secret_key" {
  name         = "secret-key"
  value        = var.app_secret_key
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_role_assignment.deployer_secrets]
}

resource "azurerm_key_vault_secret" "encryption_master_key" {
  name         = "encryption-master-key"
  value        = var.encryption_master_key
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_role_assignment.deployer_secrets]
}

resource "azurerm_key_vault_secret" "database_url" {
  name         = "database-url"
  value        = var.database_url
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_role_assignment.deployer_secrets]
}

resource "azurerm_key_vault_secret" "storage_connection_string" {
  name         = "storage-connection-string"
  value        = var.storage_connection_string
  key_vault_id = azurerm_key_vault.this.id

  depends_on = [azurerm_role_assignment.deployer_secrets]
}
