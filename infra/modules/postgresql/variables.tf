variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "container_app_environment_id" {
  type        = string
  description = "Container App Environment ID to deploy PostgreSQL into"
}

variable "storage_account_name" {
  type        = string
  description = "Storage account for persistent PostgreSQL data volume"
}

variable "admin_username" {
  type    = string
  default = "m365vault_admin"
}

variable "admin_password" {
  type      = string
  sensitive = true
}

variable "database_name" {
  type    = string
  default = "m365vault"
}

variable "sku_name" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "storage_mb" {
  type    = number
  default = 32768
}

variable "backup_retention_days" {
  type    = number
  default = 7
}

variable "geo_redundant_backup" {
  type    = bool
  default = false
}

variable "tags" {
  type    = map(string)
  default = {}
}
