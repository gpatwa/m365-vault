variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "replication_type" {
  type    = string
  default = "LRS"
}

variable "container_name" {
  type    = string
  default = "m365vault-backups"
}

variable "tags" {
  type    = map(string)
  default = {}
}
