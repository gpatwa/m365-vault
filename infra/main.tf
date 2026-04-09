terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id = var.subscription_id
}

locals {
  tags = {
    project     = "m365vault"
    environment = var.environment
    managed_by  = "terraform"
  }
}

# Generate secure passwords
resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "random_password" "secret_key" {
  length  = 64
  special = false
}

resource "random_password" "encryption_key" {
  length  = 32
  special = false
}

# ── Modules ──────────────────────────────────────────────────────────

module "resource_group" {
  source      = "./modules/resource_group"
  environment = var.environment
  location    = var.location
  tags        = local.tags
}

module "acr" {
  source              = "./modules/acr"
  environment         = var.environment
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  sku                 = var.acr_sku
  tags                = local.tags
}

module "storage" {
  source              = "./modules/storage"
  environment         = var.environment
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  replication_type    = var.storage_redundancy
  tags                = local.tags
}

# PostgreSQL — Azure Flexible Server (persistent, managed, auto-backup)
module "postgresql" {
  source              = "./modules/postgresql"
  environment         = var.environment
  resource_group_name = module.resource_group.name
  location            = var.postgresql_location != "" ? var.postgresql_location : module.resource_group.location
  admin_username      = local.db_username
  admin_password      = random_password.db_password.result
  database_name       = local.db_name
  sku_name            = var.postgresql_sku
  storage_mb          = var.postgresql_storage_mb
  tags                = local.tags
}

locals {
  db_username  = "kavachiq_admin"
  db_name      = "kavachiq"
  database_url = module.postgresql.connection_string
}

module "keyvault" {
  source                    = "./modules/keyvault"
  environment               = var.environment
  resource_group_name       = module.resource_group.name
  location                  = module.resource_group.location
  app_secret_key            = random_password.secret_key.result
  encryption_master_key     = random_password.encryption_key.result
  database_url              = local.database_url
  storage_connection_string = module.storage.connection_string
  tags                      = local.tags
}

module "redis" {
  source              = "./modules/redis"
  environment         = var.environment
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  capacity            = var.redis_capacity
  family              = var.redis_family
  sku_name            = var.redis_sku
  tags                = local.tags
}

module "container_apps" {
  source                    = "./modules/container_apps"
  environment               = var.environment
  resource_group_name       = module.resource_group.name
  location                  = module.resource_group.location
  acr_login_server          = module.acr.login_server
  acr_admin_username        = module.acr.admin_username
  acr_admin_password        = module.acr.admin_password
  image_tag                 = var.image_tag
  database_url              = local.database_url
  db_password               = random_password.db_password.result
  db_username               = local.db_username
  db_name                   = local.db_name
  storage_account_name      = module.storage.account_name
  storage_account_key       = module.storage.primary_access_key
  app_secret_key            = random_password.secret_key.result
  encryption_master_key     = random_password.encryption_key.result
  storage_connection_string = module.storage.connection_string
  storage_container_name    = module.storage.container_name
  keyvault_id               = module.keyvault.vault_id
  enable_keyvault           = true
  backend_cpu               = var.backend_cpu
  backend_memory            = var.backend_memory
  backend_min_replicas      = var.backend_min_replicas
  backend_max_replicas      = var.backend_max_replicas
  cors_origins              = var.cors_origins
  redis_url                 = module.redis.redis_url
  worker_cpu                = var.worker_cpu
  worker_memory             = var.worker_memory
  worker_min_replicas       = var.worker_min_replicas
  worker_max_replicas       = var.worker_max_replicas
  worker_concurrency        = var.worker_concurrency
  worker_scale_threshold    = var.worker_scale_threshold
  redis_enable_tls          = var.redis_enable_tls
  # Key Vault (for secret references — no secrets in Terraform state)
  keyvault_uri              = module.keyvault.vault_uri
  # Non-sensitive config (safe in state)
  stripe_publishable_key    = var.stripe_publishable_key
  stripe_price_professional = var.stripe_price_professional
  stripe_price_business     = var.stripe_price_business
  stripe_price_enterprise   = var.stripe_price_enterprise
  email_provider            = var.email_provider
  frontend_url              = var.frontend_url
  connector_app_id          = var.connector_app_id
  connector_redirect_uri    = var.connector_redirect_uri
  posthog_api_key           = var.posthog_api_key
  backend_custom_domain     = var.backend_custom_domain
  tags                      = local.tags
}
