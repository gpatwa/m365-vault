variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "acr_login_server" {
  type = string
}

variable "acr_admin_username" {
  type = string
}

variable "acr_admin_password" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "app_secret_key" {
  type      = string
  sensitive = true
}

variable "encryption_master_key" {
  type      = string
  sensitive = true
}

variable "storage_connection_string" {
  type      = string
  sensitive = true
}

variable "storage_container_name" {
  type    = string
  default = "m365vault-backups"
}

variable "cors_origins" {
  type    = string
  default = ""
}

variable "keyvault_id" {
  type    = string
  default = ""
}

variable "enable_keyvault" {
  description = "Whether Key Vault integration is enabled (avoids count depending on unknown values)"
  type        = bool
  default     = true
}

variable "backend_cpu" {
  type    = number
  default = 0.5
}

variable "backend_memory" {
  type    = string
  default = "1Gi"
}

variable "backend_min_replicas" {
  type    = number
  default = 1
}

variable "backend_max_replicas" {
  type    = number
  default = 3
}

variable "redis_url" {
  type      = string
  sensitive = true
  default   = ""
}

variable "worker_cpu" {
  type    = number
  default = 0.5
}

variable "worker_memory" {
  type    = string
  default = "1Gi"
}

variable "worker_min_replicas" {
  type    = number
  default = 1
}

variable "worker_max_replicas" {
  type    = number
  default = 3
}

variable "tags" {
  type    = map(string)
  default = {}
}
