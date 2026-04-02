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

variable "postgresql_location" {
  description = "Override location for PostgreSQL (if restricted in primary region)"
  type        = string
  default     = ""
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

# Worker
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

# Redis
variable "redis_capacity" {
  type        = number
  default     = 0
  description = "Redis cache capacity (0=250MB C0, 1=1GB C1, ...)"
}

variable "redis_family" {
  type    = string
  default = "C"
}

variable "redis_sku" {
  type        = string
  default     = "Basic"
  description = "Redis SKU: Basic (dev), Standard (prod)"
}
