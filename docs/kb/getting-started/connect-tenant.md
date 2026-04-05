# Connect Your Microsoft 365 Tenant

Connect your Microsoft 365 environment to KavachIQ in minutes using secure OAuth consent. Once connected, KavachIQ automatically discovers your workloads and prepares them for protection.

## Prerequisites

Before you begin, confirm the following:

- You have **Global Administrator** privileges in your Microsoft 365 tenant, or a delegated admin has pre-approved the KavachIQ enterprise application.
- Your tenant allows third-party enterprise application consent (check **Azure AD > Enterprise applications > Consent and permissions**).
- You have an active KavachIQ account with the **Tenant Admin** role or higher.

## Step 1: Initiate the Connection

1. Log in to the KavachIQ dashboard.
2. Navigate to **Settings > Tenants**.
3. Click **Connect Tenant**.
4. You will be redirected to the Microsoft identity platform consent screen.

## Step 2: Grant Consent

On the Microsoft consent page:

1. Sign in with your Global Administrator credentials.
2. Review the permissions KavachIQ requests. These include read access to Exchange, OneDrive, SharePoint, Teams, and Entra ID resources via the Microsoft Graph API.
3. Check **Consent on behalf of your organization**.
4. Click **Accept**.

You will be redirected back to KavachIQ automatically.

## What Happens During Connection

Once consent is granted, KavachIQ performs the following steps:

- **Credential storage**: Your OAuth tokens are encrypted at rest using AES-256-GCM with a dedicated per-tenant data encryption key. KavachIQ never stores your administrator password.
- **Automatic discovery**: A discovery job runs immediately to enumerate mailboxes, OneDrive accounts, SharePoint sites, Teams, and Entra ID objects in your tenant.
- **Health check**: KavachIQ validates API connectivity and confirms that the granted permissions are sufficient for backup operations.

The entire process typically completes in under 60 seconds for tenants with fewer than 500 users.

## Verifying the Connection

After connecting, confirm a successful setup:

1. Go to **Settings > Tenants** and verify the status shows **Connected**.
2. Navigate to **Workloads** and confirm that discovered objects (mailboxes, sites, etc.) appear in the inventory.
3. Check the **Jobs** page for the completed discovery job.

## Troubleshooting

### Consent screen does not appear

- Verify that your browser allows pop-ups from `login.microsoftonline.com`.
- Clear your browser cache and try again in an incognito/private window.
- Confirm that your Azure AD tenant has not disabled enterprise application consent.

### Consent fails with "Need admin approval"

- You must be a Global Administrator, or your tenant requires admin approval for enterprise apps. Ask your Global Admin to approve the KavachIQ application in **Azure AD > Enterprise applications > Admin consent requests**.

### Connection shows "Degraded" status

- This typically means one or more Graph API permissions were not fully granted. Disconnect and reconnect the tenant to re-trigger consent with the complete permission set.
- If the issue persists, verify there are no Conditional Access policies blocking service principal access.

### Discovery returns zero objects

- Ensure the connected account has licenses assigned (e.g., Exchange Online, OneDrive for Business). Unlicensed tenants will return empty results.
- Check that the tenant is not in a suspended or grace-period state.

## Security Notes

- KavachIQ uses the OAuth 2.0 authorization code flow with PKCE. No client secrets are stored in the browser.
- All tokens are encrypted with AES-256-GCM before being written to the database.
- You can revoke KavachIQ access at any time from **Azure AD > Enterprise applications > KavachIQ > Properties > Delete**.

## Next Steps

Once your tenant is connected, proceed to [Discover Your Workloads](discover-workloads.md) to review and customize which workloads are protected.
