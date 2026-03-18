#!/usr/bin/env bash
# Import existing Azure resources into Terraform state
set -euo pipefail

SUB="fb665ec0-d69f-49ef-a6e8-40b4a805ad8e"
RG="rg-m365vault-dev"
TF_ARGS='-var-file=environments/dev.tfvars -var="subscription_id='"$SUB"'"'

cd "$(dirname "$0")/../infra"

import_if_missing() {
  local addr="$1"
  local id="$2"
  if terraform state show "$addr" >/dev/null 2>&1; then
    echo "  ✓ $addr (already in state)"
  else
    echo "  → Importing $addr..."
    eval terraform import $TF_ARGS "'$addr'" "'$id'" 2>&1 | tail -1
  fi
}

echo "Importing existing Azure resources into Terraform state..."
echo ""

import_if_missing "module.resource_group.azurerm_resource_group.this" \
  "/subscriptions/$SUB/resourceGroups/$RG"

import_if_missing "module.acr.azurerm_container_registry.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.ContainerRegistry/registries/acrm365vaultdev"

import_if_missing "module.storage.azurerm_storage_account.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.Storage/storageAccounts/stm365vaultdev"

import_if_missing "module.storage.azurerm_storage_container.backups" \
  "https://stm365vaultdev.blob.core.windows.net/backups"

import_if_missing "module.postgresql.azurerm_postgresql_flexible_server.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-m365vault-dev"

import_if_missing "module.postgresql.azurerm_postgresql_flexible_server_database.m365vault" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-m365vault-dev/databases/m365vault"

import_if_missing "module.postgresql.azurerm_postgresql_flexible_server_firewall_rule.azure_services" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-m365vault-dev/firewallRules/AllowAzureServices"

import_if_missing "module.keyvault.azurerm_key_vault.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.KeyVault/vaults/kv-m365vault-dev"

import_if_missing "module.container_apps.azurerm_log_analytics_workspace.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.OperationalInsights/workspaces/log-m365vault-dev"

import_if_missing "module.container_apps.azurerm_container_app_environment.this" \
  "/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.App/managedEnvironments/cae-m365vault-dev"

echo ""
echo "✅ Import complete. Run 'make tf-apply' to reconcile."
