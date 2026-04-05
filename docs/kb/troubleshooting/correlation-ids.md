# Using Correlation IDs

Every request processed by KavachIQ is assigned a unique correlation ID. This identifier follows the request through every layer of the system, making it possible to trace a single operation from the browser all the way to the Microsoft Graph API. When you contact support, providing a correlation ID allows the team to locate your specific request instantly.

## What Is a Correlation ID?

A correlation ID is a UUID v4 string (e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890`) generated at the start of each API request. It is attached to every log entry, database operation, and external API call made while processing that request.

## Where to Find Correlation IDs

### HTTP Response Header

Every API response includes the correlation ID in the `X-Correlation-ID` header:

```
HTTP/1.1 200 OK
X-Correlation-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
Content-Type: application/json
```

If you are making API calls directly (via curl, Postman, or scripts), capture this header from the response.

### Error Response Body

All error responses include the correlation ID in the JSON body:

```json
{
  "code": "E3001",
  "message": "Graph API throttled",
  "detail": "429 received for GET /users/user@contoso.com/messages",
  "fix": "No action required. Automatic retry scheduled.",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### Dashboard Error Boundary

When an unhandled error occurs in the KavachIQ web dashboard, the ErrorBoundary component displays a user-friendly error screen that includes the correlation ID. Copy this value before navigating away.

### Job Detail Page

Each backup or restore job displays its correlation ID on the job detail page under **Job Info > Correlation ID**.

## How Correlation IDs Flow Through the System

```
Browser (React)
  |-- X-Correlation-ID in request header
  v
Backend (FastAPI)
  |-- Logs every operation with the correlation ID
  |-- Passes correlation ID to Graph API calls via client-request-id header
  v
Microsoft Graph API
  |-- Logs the client-request-id on Microsoft's side
  v
Storage / Database
  |-- Records correlation ID in audit log entries
```

This end-to-end tracing means that a single correlation ID can be used to:

- Find the original API request and its parameters.
- See which Graph API calls were made and their responses.
- Identify throttling, errors, or latency at each layer.
- Match the request to Microsoft's own server-side logs if an escalation to Microsoft is needed.

## Sharing Correlation IDs with Support

When opening a support ticket or contacting the KavachIQ team:

1. **Include the correlation ID** -- this is the single most useful piece of information for debugging.
2. **Note the approximate time** the error occurred (with timezone).
3. **Describe the action** you were performing (e.g., "started a backup for Exchange workload").
4. **Include the error code** if one was returned (e.g., E3001).

With a correlation ID, the support team can typically identify the root cause within minutes rather than hours.

## Generating Your Own Correlation IDs

If you are building automation against the KavachIQ API, you can pass your own correlation ID in the request header:

```
X-Correlation-ID: my-custom-id-12345
```

If provided, KavachIQ uses your value instead of generating a new one. This is useful for correlating KavachIQ API calls with your own internal systems.

## Tips

- Correlation IDs are included in the append-only audit log and are retained for the full audit retention period.
- When Microsoft Graph returns a `request-id` header, KavachIQ logs it alongside the correlation ID, enabling cross-vendor tracing.
- If you lose a correlation ID, the support team can still search by tenant, user, timestamp, and error code -- but it takes longer.
