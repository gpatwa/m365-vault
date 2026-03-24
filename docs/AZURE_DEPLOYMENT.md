# Azure Deployment Guide

Deploy Shieldio to Azure using Terraform (infrastructure) and GitHub Actions (CI/CD).

## Architecture

| Service | Azure Resource | Purpose |
|---------|---------------|---------|
| Backend | Container Apps | FastAPI application (internal ingress) |
| Frontend | Container Apps | React/nginx (external HTTPS) |
| Database | PostgreSQL Flexible Server | Production database |
| Storage | Blob Storage | Encrypted backup blobs |
| Secrets | Key Vault | SECRET_KEY, ENCRYPTION_MASTER_KEY, connection strings |
| Images | Container Registry (ACR) | Docker image repository |

## Automated Setup (Recommended)

The entire Azure + GitHub setup is automated via a single command. The bootstrap
script auto-installs all prerequisites, authenticates with Azure and GitHub
via browser-based login (no tokens or passwords needed), and configures everything.

```bash
# From project root — that's it!
make bootstrap
```

**What `make bootstrap` does automatically:**

| Step | Action | Details |
|------|--------|---------|
| 1 | **Install prerequisites** | Installs `az`, `gh`, `jq`, `terraform` via Homebrew if missing |
| 2 | **Authenticate Azure** | Opens browser for Azure login (device code flow) |
| 3 | **Authenticate GitHub** | Opens browser for GitHub login (OAuth web flow) |
| 4 | **Create service principal** | Creates `sp-m365vault-github` with Contributor role + OIDC |
| 5 | **Create OIDC credentials** | Federated credentials for `main` branch and pull requests |
| 6 | **Create Terraform state** | Resource group + Storage Account + blob container for remote state |
| 7 | **Set GitHub secrets** | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` |
| 8 | **Enable remote backend** | Generates `infra/backend.tf` for team collaboration |

**No manual steps required** — no tokens to generate, no secrets to copy, no Portal clicks.

### Bootstrap with Subscription ID

```bash
# Skip the subscription selection prompt
make bootstrap SUBSCRIPTION_ID=fb665ec0-d69f-49ef-a6e8-40b4a805ad8e

# Or run the script directly
./scripts/bootstrap-azure.sh --subscription <YOUR_SUBSCRIPTION_ID>
```

## Deploy Infrastructure

After bootstrap, deploy the Azure resources:

```bash
# Plan (review what will be created)
make tf-plan ENV=dev SUBSCRIPTION_ID=<YOUR_SUBSCRIPTION_ID>

# Apply (create resources)
make tf-apply ENV=dev SUBSCRIPTION_ID=<YOUR_SUBSCRIPTION_ID>

# Set ACR secrets in GitHub (auto-reads from terraform output)
make tf-set-acr-secrets

# Destroy (tear down everything)
make tf-destroy ENV=dev SUBSCRIPTION_ID=<YOUR_SUBSCRIPTION_ID>
```

### First-Time Azure Provider Registration

If you get `MissingSubscriptionRegistration` errors, register the required providers:

```bash
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

# Check registration status
az provider show --namespace Microsoft.App --query "registrationState" -o tsv
```

This is a one-time step per Azure subscription and takes 1-2 minutes.

## CI/CD Pipeline

Once bootstrap and first deploy are complete, CI/CD is fully automatic:

| Trigger | Action |
|---------|--------|
| Push to `main` | Build Docker images → push to ACR → deploy to dev |
| Pull request | Build + test only (no deploy) |
| Manual dispatch | Deploy to prod (with approval gate) |

### Monitor Deployments

```bash
make deploy-status         # Show recent GitHub Actions runs
make deploy-dev            # Manually trigger dev deployment
make deploy-prod           # Trigger prod deployment (with confirmation)
```

## Environment Configuration

### Dev vs Prod Sizing

| Resource | Dev | Prod |
|----------|-----|------|
| PostgreSQL | B_Standard_B1ms (Burstable) | GP_Standard_D2s_v3 (General Purpose) |
| Storage | LRS (locally redundant) | GRS (geo-redundant) |
| Backend CPU | 0.5 cores | 1.0 core |
| Backend Memory | 1 Gi | 2 Gi |
| Backend Replicas | 1-3 | 2-10 |
| ACR SKU | Basic | Standard |

### Environment Variables

The following are configured automatically via Key Vault:

| Variable | Source | Description |
|----------|--------|-------------|
| `SECRET_KEY` | Key Vault | JWT signing key (auto-generated) |
| `ENCRYPTION_MASTER_KEY` | Key Vault | AES-256 master key (auto-generated) |
| `DATABASE_URL` | Key Vault | PostgreSQL connection string |
| `AZURE_STORAGE_CONNECTION_STRING` | Key Vault | Blob Storage connection |

### Terraform State

Remote state is stored in Azure Blob Storage (created by bootstrap):

| Resource | Name |
|----------|------|
| Resource Group | `rg-m365vault-tfstate` |
| Storage Account | `stm365vaulttfstate` |
| Container | `tfstate` |
| State File | `m365vault.terraform.tfstate` |

## Seed Test Data (Dev)

After deploying to dev, seed the simulation data:

```bash
# Via Docker (local)
make seed

# Via Azure Container Apps
az containerapp exec \
  --name m365vault-backend-dev \
  --resource-group rg-m365vault-dev \
  --command "python3 /scripts/simulate_backup_data.py"
```

## Production Deployment

```bash
# Option 1: Terraform directly
make tf-apply ENV=prod SUBSCRIPTION_ID=<YOUR_SUBSCRIPTION_ID>

# Option 2: GitHub Actions (with approval gate)
make deploy-prod
```

For production, ensure:

1. **PostgreSQL** is General Purpose tier (not Burstable)
2. **Storage** uses GRS (geo-redundant) replication
3. **Key Vault** has soft-delete and purge protection enabled
4. **Network** has private endpoints for PostgreSQL and Storage
5. **Monitoring** has Azure Monitor and alerts configured

## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `MissingSubscriptionRegistration` | Azure provider not registered | `az provider register --namespace Microsoft.App` |
| `LocationIsOfferRestricted` | PostgreSQL not available in region | Change region in `dev.tfvars` (e.g., `westus2`) |
| `count depends on resource attributes` | Terraform conditional on runtime value | Use boolean variable instead of resource attribute in `count` |
| `Backend initialization required` | Remote state not initialized | `make tf-init` or run bootstrap first |

### Cleanup

```bash
# Destroy all dev resources
make tf-destroy ENV=dev SUBSCRIPTION_ID=<YOUR_SUBSCRIPTION_ID>

# Or delete resource group directly (fastest)
az group delete --name rg-m365vault-dev --yes --no-wait

# Remove tfstate storage (only if decommissioning)
az group delete --name rg-m365vault-tfstate --yes
```

## Quick Reference — All Make Commands

```bash
make help                  # Show all available commands

# Local Development
make dev                   # Start Docker Compose (postgres + minio + backend + frontend)
make dev-bg                # Start in background
make dev-down              # Stop all services
make dev-clean             # Stop + remove volumes (fresh start)
make seed                  # Seed simulated backup data
make seed-clean            # Clean DB + storage, then re-seed
make build                 # Build Docker images locally

# Azure Deployment
make bootstrap             # One-time setup: installs tools, creates SP, OIDC, tfstate, secrets
make tf-init               # Initialize Terraform backend
make tf-plan               # Plan infrastructure changes
make tf-apply              # Apply infrastructure changes
make tf-destroy            # Destroy infrastructure (with confirmation)
make tf-set-acr-secrets    # Set ACR GitHub secrets from Terraform output
make deploy-dev            # Trigger dev deployment via GitHub Actions
make deploy-prod           # Trigger prod deployment (with confirmation)
make deploy-status         # Show recent CI/CD runs
make check-prereqs         # Verify all tools are installed
```
