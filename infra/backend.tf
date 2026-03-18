# Terraform remote state storage in Azure
# Uncomment and configure after creating the storage account:
#
# 1. Create state storage (one-time):
#    az group create -n rg-m365vault-tfstate -l eastus
#    az storage account create -n stm365vaulttfstate -g rg-m365vault-tfstate -l eastus --sku Standard_LRS
#    az storage container create -n tfstate --account-name stm365vaulttfstate
#
# 2. Uncomment this block:
#
# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rg-m365vault-tfstate"
#     storage_account_name = "stm365vaulttfstate"
#     container_name       = "tfstate"
#     key                  = "m365vault.terraform.tfstate"
#   }
# }
