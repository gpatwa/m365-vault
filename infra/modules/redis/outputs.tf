output "redis_url" {
  value     = "rediss://:${azurerm_redis_cache.this.primary_access_key}@${azurerm_redis_cache.this.hostname}:${azurerm_redis_cache.this.ssl_port}/0"
  sensitive = true
}

output "hostname" {
  value = azurerm_redis_cache.this.hostname
}
