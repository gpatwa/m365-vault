# Fixing Connection Failures

A healthy connection between KavachIQ and your Microsoft 365 tenant is required before backups can run. This article covers common causes of connection failures, how to diagnose them, and step-by-step fixes for each error code.

## Diagnostic Endpoints

Before troubleshooting individual errors, check overall system health:

| Endpoint | Purpose |
|---|---|
| `GET /api/diagnostics/health` | Returns status of database, storage, and external dependencies. |
| `GET /api/onboard/connector-health` | Tests the Microsoft 365 connector by attempting a token acquisition and a lightweight Graph API call. |

If `/api/diagnostics/health` shows all services healthy but `/api/onboard/connector-health` fails, the issue is isolated to the Microsoft 365 connection.

## Common Causes

### 1. App Registration Not Configured (E1001)

**Symptom**: Connector health returns E1001.

**Fix**:
- Open the KavachIQ dashboard and navigate to **Settings > Connectors**.
- Enter your Azure AD Application (client) ID and Directory (tenant) ID.
- Save and re-test connector health.

### 2. Client Secret Invalid or Expired (E1002)

**Symptom**: Connector health returns E1002. Token acquisition fails with `invalid_client`.

**Fix**:
- Open the [Azure Portal](https://portal.azure.com) and navigate to **Azure Active Directory > App registrations > your app > Certificates & secrets**.
- Check the expiration date of the current secret.
- If expired, create a new secret, copy the value, and update it in **Settings > Connectors**.
- Secrets cannot be viewed after creation in Azure. If you lost the value, you must generate a new one.

### 3. Admin Consent Not Granted (E1003)

**Symptom**: Connector health returns E1003. Graph API calls return `Authorization_RequestDenied`.

**Fix**:
- An Azure AD Global Administrator must visit the admin consent URL shown in the error detail.
- The URL format is: `https://login.microsoftonline.com/{tenant}/adminconsent?client_id={app_id}`
- After granting consent, wait 1-2 minutes for propagation, then re-test.
- In the Azure Portal, verify consent under **Enterprise applications > your app > Permissions**. All required permissions should show "Granted for [tenant]".

### 4. Tenant Not Found (E1004)

**Symptom**: Connector health returns E1004. Token endpoint returns `tenant_not_found`.

**Fix**:
- Verify the Tenant ID in **Settings > Connectors** matches your Azure AD directory.
- Open the Azure Portal, navigate to **Azure Active Directory > Overview**, and confirm the Directory (tenant) ID.
- Copy-paste the ID to avoid transcription errors.

### 5. Token Acquisition Failed (E1005)

**Symptom**: Connector health returns E1005. This is a catch-all for OAuth2 failures not covered by E1002-E1004.

**Fix**:
- Verify all three values: Application ID, Tenant ID, and client secret.
- Confirm the app registration has not been deleted in Azure AD.
- Check that the app registration has the required API permissions added (not just consented).
- If using a multi-tenant app, ensure the service principal exists in the target tenant.

### 6. Graph API Unreachable (E1006)

**Symptom**: Connector health returns E1006. Network-level timeout or DNS failure.

**Fix**:
- Check [Microsoft 365 service health](https://status.office.com) for active incidents.
- Verify the KavachIQ host can resolve and reach `graph.microsoft.com` on port 443.
- If behind a corporate firewall or proxy, ensure `login.microsoftonline.com` and `graph.microsoft.com` are allowlisted.
- For Azure-hosted deployments, check the Network Security Group (NSG) rules for outbound HTTPS.

## Azure Portal Navigation Tips

When verifying your app registration in the Azure Portal:

1. Sign in at [portal.azure.com](https://portal.azure.com).
2. Search for **App registrations** in the top search bar.
3. Select the app registration used by KavachIQ.
4. Check **Overview** for Application ID and Tenant ID.
5. Check **Certificates & secrets** for secret expiration.
6. Check **API permissions** for required Graph API scopes.
7. Switch to **Enterprise applications** to verify admin consent status.

## Still Having Issues?

If the above steps do not resolve the connection failure, open a support ticket and include:

- The correlation ID from the error response.
- The output of `/api/diagnostics/health`.
- The output of `/api/onboard/connector-health`.
- The Azure AD Application ID (not the secret).
