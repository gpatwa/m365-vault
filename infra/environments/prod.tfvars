environment           = "prod"
location              = "eastus"

# ACR
acr_sku               = "Standard"

# PostgreSQL — General Purpose for prod
postgresql_sku        = "GP_Standard_D2s_v3"
postgresql_storage_mb = 65536

# Storage — geo-redundant for prod
storage_redundancy    = "GRS"

# Container Apps — production sizing
backend_cpu           = 1.0
backend_memory        = "2Gi"
backend_min_replicas  = 2
backend_max_replicas  = 10

# Worker — production sizing
worker_cpu            = 1.0
worker_memory         = "2Gi"
worker_min_replicas   = 2
worker_max_replicas   = 6

# Redis — Standard C1 for prod (replicated, ~$75/mo)
redis_sku             = "Standard"
redis_capacity        = 1
redis_family          = "C"
