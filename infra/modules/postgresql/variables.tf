variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "admin_username" {
  type    = string
  default = "kavachiq_admin"
}

variable "admin_password" {
  type      = string
  sensitive = true
}

variable "database_name" {
  type    = string
  default = "kavachiq"
}

variable "sku_name" {
  type        = string
  default     = "B_Standard_B1ms"
  description = "B1ms: 1 vCore, 2 GB RAM (~$13/mo)"
}

variable "storage_mb" {
  type    = number
  default = 32768
}

variable "tags" {
  type    = map(string)
  default = {}
}
