environment           = "dev"
location              = "centralus"

# ACR
acr_sku               = "Basic"

# PostgreSQL — Burstable for dev
postgresql_sku        = "B_Standard_B1ms"
postgresql_storage_mb = 32768

# Storage — locally redundant for dev
storage_redundancy    = "LRS"

# Container Apps — small for dev
backend_cpu           = 0.5
backend_memory        = "1Gi"
backend_min_replicas  = 1
backend_max_replicas  = 3

# Worker — small for dev
worker_cpu            = 0.5
worker_memory         = "1Gi"
worker_min_replicas   = 1
worker_max_replicas   = 2

# Redis — Basic C0 for dev (~$16/mo)
redis_sku             = "Basic"
redis_capacity        = 0
redis_family          = "C"
