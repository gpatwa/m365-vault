output "backend_fqdn" {
  value = azurerm_container_app.backend.ingress[0].fqdn
}

output "frontend_fqdn" {
  value = azurerm_container_app.frontend.ingress[0].fqdn
}

output "frontend_url" {
  value = "https://${azurerm_container_app.frontend.ingress[0].fqdn}"
}

output "environment_id" {
  value = azurerm_container_app_environment.this.id
}
