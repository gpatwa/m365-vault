# Error Code Reference

Every Shieldio API response that indicates a failure includes a structured JSON error body. Understanding error codes helps you diagnose issues quickly and take the right corrective action.

## Error Response Format

All errors follow a consistent JSON structure:

```json
{
  "code": "E3001",
  "message": "Graph API throttled",
  "detail": "Microsoft returned 429 Too Many Requests for mailbox user@contoso.com",
  "fix": "Wait for the current backup window to complete. Shieldio automatically retries with exponential backoff.",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

| Field | Description |
|---|---|
| `code` | Unique error identifier (e.g., E3001). Use this when searching docs or contacting support. |
| `message` | Short human-readable summary of the problem. |
| `detail` | Contextual information specific to the failed request. |
| `fix` | Recommended next step to resolve the issue. |
| `correlation_id` | Unique request identifier for tracing through logs. Always include this when contacting support. |

## E1xxx -- Connector Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E1001 | Connector not configured | Navigate to Settings > Connectors and register your Azure AD app. Provide the Application ID and Tenant ID. | No app registration has been linked to Shieldio. |
| E1002 | Client secret invalid | Rotate the client secret in Azure Portal, then update it in Settings > Connectors. | The stored secret has expired or was revoked. |
| E1003 | Admin consent pending | An Azure AD Global Admin must grant consent at the URL provided in the error detail. | Required Graph API permissions have not been consented. |
| E1004 | Tenant not found | Verify the Tenant ID in Settings > Connectors matches your Azure AD directory. | The configured tenant does not exist or is unreachable. |
| E1005 | Token acquisition failed | Check that the Application ID, Tenant ID, and client secret are all correct and that the app registration has not been deleted. | OAuth2 client credentials flow returned an error. |
| E1006 | Graph API unreachable | Check Microsoft 365 service health at status.office.com. If healthy, verify your network allows outbound HTTPS to graph.microsoft.com. | Network-level failure connecting to Microsoft Graph. |

## E2xxx -- Authentication Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E2001 | Invalid credentials | Re-enter your email and password. If using SSO, verify your identity provider configuration. | Login attempt failed authentication. |
| E2002 | Token expired | Sign out and sign back in. If using the API, request a new token from /api/auth/login. | Your session or API token has expired. |
| E2003 | Account disabled | Contact your Shieldio administrator to re-enable the account. | The user account has been deactivated by an admin. |
| E2004 | Insufficient permissions | Contact your Shieldio administrator to assign the required role (admin, operator, or viewer). | Your role does not have permission for the requested action. |
| E2005 | Rate limited | Wait 60 seconds before retrying. If persistent, check for automated scripts sending excessive requests. | Too many authentication attempts in a short period. |

## E3xxx -- Backup Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E3001 | Graph API throttled | No action required. Shieldio automatically retries with exponential backoff and reduced concurrency. | Microsoft returned HTTP 429. See [Graph Throttling](/docs/kb/troubleshooting/graph-throttling.md). |
| E3002 | Storage write failed | Check storage health at /api/diagnostics/health. For Azure Blob, verify the storage account is accessible. | The backup payload could not be written to storage. |
| E3003 | No objects to back up | Verify that workload discovery has completed and that at least one object (mailbox, site, etc.) is selected. | The backup job found zero eligible objects. |
| E3004 | Backup already running | Wait for the current job to finish or cancel it from the Jobs page before starting a new one. | A backup job for this tenant and workload is already in progress. |
| E3005 | Tenant not connected | Complete the connector setup in Settings > Connectors before running a backup. | No valid Microsoft 365 connector exists for this tenant. |

## E4xxx -- Recovery Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E4001 | No snapshot available | Confirm that at least one successful backup has completed for the selected workload and date range. | The requested restore point does not exist. |
| E4002 | Malware detected | The snapshot contains content flagged by the malware scanner. Contact support for assisted recovery with quarantine options. | Integrity scan found a threat in the backup data. |
| E4003 | Permission denied | Verify your role has restore permissions and that the target mailbox or site allows write access via Graph API. | The restore operation was rejected due to authorization. |

## E5xxx -- Infrastructure Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E5001 | Storage unavailable | Check /api/diagnostics/health for storage status. For Azure deployments, verify the storage account in the Azure Portal. | The storage backend is not responding. |
| E5002 | Database error | Check /api/diagnostics/health for database status. If the issue persists, contact support with your correlation ID. | A database query failed or the connection was lost. |

## E6xxx -- Validation Errors

| Code | Message | Fix | Context |
|---|---|---|---|
| E6001 | Invalid input | Review the error detail for which field failed validation and correct the request payload. | A request parameter did not pass schema validation. |
| E6002 | Resource not found | Verify the ID or path in your request. The resource may have been deleted. | The requested entity does not exist. |
| E6003 | Duplicate resource | A resource with the same unique identifier already exists. Use an update operation instead. | A create operation conflicted with an existing record. |

## E7xxx -- Rate Limiting

| Code | Message | Fix | Context |
|---|---|---|---|
| E7001 | Rate limit exceeded | Reduce request frequency. The default limit is 100 requests per minute per user. Wait for the Retry-After header duration. | API rate limit reached. The response includes a Retry-After header. |

## Tips

- **Always include the correlation_id** when opening a support ticket. It lets the team trace your request across every service layer.
- **Check /api/diagnostics/health** first for any E5xxx errors. Infrastructure issues often resolve themselves within minutes.
- **Error codes are stable** across Shieldio versions. You can safely build automation around them.
