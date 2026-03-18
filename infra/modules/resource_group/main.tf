resource "azurerm_resource_group" "this" {
  name     = "rg-m365vault-${var.environment}"
  location = var.location

  tags = var.tags
}
