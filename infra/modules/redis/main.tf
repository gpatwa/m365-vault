resource "azurerm_redis_cache" "this" {
  name                          = "redis-m365vault-${var.environment}"
  location                      = var.location
  resource_group_name           = var.resource_group_name
  capacity                      = var.capacity
  family                        = var.family
  sku_name                      = var.sku_name
  non_ssl_port_enabled          = false
  minimum_tls_version           = "1.2"

  redis_configuration {}

  tags = var.tags
}
