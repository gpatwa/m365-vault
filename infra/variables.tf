variable "subscription_id" {
  type        = string
  description = "Azure subscription ID"
}

variable "environment" {
  type        = string
  description = "Environment name (dev, prod)"
  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Environment must be 'dev' or 'prod'."
  }
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "image_tag" {
  type    = string
  default = "latest"
}

# ACR
variable "acr_sku" {
  type    = string
  default = "Basic"
}

# PostgreSQL
variable "postgresql_sku" {
  type    = string
  default = "B_Standard_B1ms"
}

variable "postgresql_storage_mb" {
  type    = number
  default = 32768
}

# Storage
variable "storage_redundancy" {
  type    = string
  default = "LRS"
}

# Container Apps
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

variable "cors_origins" {
  type        = string
  default     = ""
  description = "Comma-separated CORS origins for the backend"
}
