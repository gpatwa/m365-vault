variable "environment" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "capacity" {
  type        = number
  default     = 0
  description = "Redis cache size (0=250MB, 1=1GB, 2=6GB, ...)"
}

variable "family" {
  type    = string
  default = "C"
}

variable "sku_name" {
  type        = string
  default     = "Basic"
  description = "Redis SKU: Basic, Standard, or Premium"
}

variable "tags" {
  type    = map(string)
  default = {}
}
