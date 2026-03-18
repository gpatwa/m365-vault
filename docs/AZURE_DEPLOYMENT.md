# Azure Deployment Guide

Deploy M365 Vault to Azure using Terraform (infrastructure) and GitHub Actions (CI/CD).

## Architecture

| Service | Azure Resource | Purpose |
|---------|---------------|---------|
| Backend | Container Apps | FastAPI application (internal ingress) |
| Frontend | Container Apps | React/nginx (external HTTPS) |
| Database | PostgreSQL Flexible Server | Production database |
| Storage | Blob Storage | Encrypted backup blobs |
| Secrets | Key Vault | SECRET_KEY, ENCRYPTION_MASTER_KEY, connection strings |
| Images | Container Registry (ACR) | Docker image repository |

## Prerequisites

- Azure CLI (`az`) installed and logged in
- Terraform >= 1.5 installed
- GitHub repository with Actions enabled
- Azure subscription ID

## Step 1: Create Service Principal for GitHub Actions

```bash
# Create service principal with Contributor role
az ad sp create-for-rbac \
  --name "sp-m365vault-github" \
  --role Contributor \
  --scopes /subscriptions/<SUBSCRIPTION_ID> \
  --sdk-auth

# Create federated credential for OIDC (no stored secrets)
az ad app federated-credential create \
  --id <APP_ID> \
  --parameters '{
    "name": "github-main",
    "issuer": "https://token.actions.githubusercontent.com",
    "subject": "repo:<GITHUB_ORG>/<GITHUB_REPO>:ref:refs/heads/main",
    "audiences": ["api://AzureADTokenExchange"]
  }'
```

## Step 2: Configure GitHub Secrets

Go to GitHub repo > Settings > Secrets and variables > Actions:

| Secret | Value |
|--------|-------|
| `AZURE_CLIENT_ID` | Service principal App ID |
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_SUBSCRIPTION_ID` | Subscription ID |
| `ACR_NAME` | ACR name (e.g., `acrm365vaultdev`) |
| `ACR_LOGIN_SERVER` | ACR login server (e.g., `acrm365vaultdev.azurecr.io`) |

## Step 3: Deploy Dev Environment

```bash
cd infra

# Initialize Terraform
terraform init

# Preview changes
terraform plan \
  -var-file=environments/dev.tfvars \
  -var="subscription_id=<YOUR_SUBSCRIPTION_ID>"

# Apply
terraform apply \
  -var-file=environments/dev.tfvars \
  -var="subscription_id=<YOUR_SUBSCRIPTION_ID>"
```

After apply, note the outputs:
- `frontend_url` — public URL for the application
- `acr_login_server` — where to push Docker images

## Step 4: Push Docker Images

```bash
# Login to ACR
az acr login --name acrm365vaultdev

# Build and push
docker build -t acrm365vaultdev.azurecr.io/m365vault-backend:latest ./backend
docker push acrm365vaultdev.azurecr.io/m365vault-backend:latest

docker build -t acrm365vaultdev.azurecr.io/m365vault-frontend:latest ./frontend
docker push acrm365vaultdev.azurecr.io/m365vault-frontend:latest
```

## Step 5: Seed Test Data

```bash
az containerapp exec \
  --name m365vault-backend-dev \
  --resource-group rg-m365vault-dev \
  --command "python3 /scripts/simulate_backup_data.py"
```

## Step 6: CI/CD (Automatic)

Once GitHub secrets are configured:
- **Push to main** → auto-deploys to dev
- **Manual dispatch** → deploy to prod (with approval gate)

## Production Deployment

```bash
# Deploy production
terraform apply \
  -var-file=environments/prod.tfvars \
  -var="subscription_id=<YOUR_SUBSCRIPTION_ID>"
```

Or trigger via GitHub Actions:
1. Go to Actions > Deploy > Run workflow
2. Select environment: `prod`
3. Approve the deployment in the `production` environment gate

## Environment Sizing

| Resource | Dev | Prod |
|----------|-----|------|
| PostgreSQL | B_Standard_B1ms (Burstable) | GP_Standard_D2s_v3 (General Purpose) |
| Storage | LRS (locally redundant) | GRS (geo-redundant) |
| Backend CPU | 0.5 cores | 1.0 core |
| Backend Memory | 1 Gi | 2 Gi |
| Backend Replicas | 1-3 | 2-10 |
| ACR SKU | Basic | Standard |

## Terraform State

For team collaboration, enable remote state:

```bash
# Create state storage (one-time)
az group create -n rg-m365vault-tfstate -l eastus
az storage account create -n stm365vaulttfstate -g rg-m365vault-tfstate --sku Standard_LRS
az storage container create -n tfstate --account-name stm365vaulttfstate
```

Then uncomment the backend block in `infra/backend.tf`.
