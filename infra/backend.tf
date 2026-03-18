# Terraform remote state storage in Azure
#
# This backend is configured via -backend-config flags in CI/CD (deploy.yml)
# and via bootstrap-azure.sh for local development.
#
# To use locally after bootstrap:
#   cd infra
#   terraform init \
#     -backend-config="resource_group_name=rg-m365vault-tfstate" \
#     -backend-config="storage_account_name=stm365vaulttfstate" \
#     -backend-config="container_name=tfstate" \
#     -backend-config="key=m365vault.terraform.tfstate"

terraform {
  backend "azurerm" {
    resource_group_name  = "rg-m365vault-tfstate"
    storage_account_name = "stm365vaulttfstate"
    container_name       = "tfstate"
    key                  = "m365vault.terraform.tfstate"
    use_oidc             = true
  }
}
