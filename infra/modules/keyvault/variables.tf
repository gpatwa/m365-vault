variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "app_secret_key" {
  type      = string
  sensitive = true
}

variable "encryption_master_key" {
  type      = string
  sensitive = true
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "storage_connection_string" {
  type      = string
  sensitive = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
