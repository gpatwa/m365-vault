output "frontend_url" {
  value       = module.container_apps.frontend_url
  description = "Public URL of the frontend application"
}

output "backend_fqdn" {
  value       = module.container_apps.backend_fqdn
  description = "Internal FQDN of the backend (used by frontend nginx)"
}

output "acr_login_server" {
  value       = module.acr.login_server
  description = "ACR login server for docker push"
}

output "postgresql_fqdn" {
  value       = module.postgresql.fqdn
  description = "PostgreSQL server FQDN"
}

output "storage_account" {
  value       = module.storage.account_name
  description = "Azure Storage account name"
}

output "resource_group" {
  value       = module.resource_group.name
  description = "Resource group name"
}
