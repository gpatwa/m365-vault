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
      purge_soft_delete_on_destroy = true
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

module "postgresql" {
  source              = "./modules/postgresql"
  environment         = var.environment
  resource_group_name = module.resource_group.name
  location            = module.resource_group.location
  admin_password      = random_password.db_password.result
  sku_name            = var.postgresql_sku
  storage_mb          = var.postgresql_storage_mb
  geo_redundant_backup = var.environment == "prod"
  tags                = local.tags
}

module "keyvault" {
  source                    = "./modules/keyvault"
  environment               = var.environment
  resource_group_name       = module.resource_group.name
  location                  = module.resource_group.location
  app_secret_key            = random_password.secret_key.result
  encryption_master_key     = random_password.encryption_key.result
  database_url              = module.postgresql.connection_string
  storage_connection_string = module.storage.connection_string
  tags                      = local.tags
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
  database_url              = module.postgresql.connection_string
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
  tags                      = local.tags
}
