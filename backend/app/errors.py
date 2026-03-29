"""Shieldio Error Code System — standardized error codes and structured error responses.

Every API error includes a machine-readable code, human-readable message,
actionable fix suggestion, and correlation ID for support tracing.

Error code ranges:
  E1xxx — Connector / M365 integration
  E2xxx — Authentication & authorization
  E3xxx — Backup operations
  E4xxx — Recovery / restore operations
  E5xxx — Storage & infrastructure
  E6xxx — Validation & input
  E7xxx — Rate limiting & quotas
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ErrorDef:
    """Definition for a Shieldio error code."""
    code: str
    status: int
    message: str
    fix: str = ""

    def response(
        self,
        request: Request | None = None,
        detail: str = "",
        extra: dict[str, Any] | None = None,
    ) -> JSONResponse:
        """Build a standardized JSON error response."""
        correlation_id = ""
        if request:
            correlation_id = getattr(request.state, "correlation_id", "")

        body: dict[str, Any] = {
            "error": {
                "code": self.code,
                "message": self.message,
                "detail": detail or self.message,
                "fix": self.fix,
                "correlation_id": correlation_id,
            }
        }
        if extra:
            body["error"].update(extra)

        logger.warning(
            "ErrorResponse code=%s status=%d detail=%s cid=%s",
            self.code, self.status, detail or self.message, correlation_id,
        )
        return JSONResponse(status_code=self.status, content=body)


class ShieldioError(Exception):
    """Raise from service code to produce a structured API error."""

    def __init__(self, error_def: ErrorDef, detail: str = "", extra: dict[str, Any] | None = None):
        self.error_def = error_def
        self.detail = detail
        self.extra = extra
        super().__init__(detail or error_def.message)


# ── Connector Errors (E1xxx) ──────────────────────────────────────

CONNECTOR_NOT_CONFIGURED = ErrorDef(
    code="E1001", status=400,
    message="Microsoft 365 connector is not configured",
    fix="Go to Settings → Microsoft 365 Connector and enter the App ID and Secret",
)
CONNECTOR_SECRET_INVALID = ErrorDef(
    code="E1002", status=401,
    message="The connector app secret is invalid or expired",
    fix="Regenerate the client secret in Azure Portal → App Registrations → Certificates & Secrets",
)
CONNECTOR_CONSENT_PENDING = ErrorDef(
    code="E1003", status=403,
    message="Admin consent has not been granted for the connector app",
    fix="An Azure AD admin must grant consent at the admin consent URL",
)
CONNECTOR_TENANT_NOT_FOUND = ErrorDef(
    code="E1004", status=404,
    message="The specified Microsoft 365 tenant was not found",
    fix="Verify the tenant ID or domain and try reconnecting",
)
CONNECTOR_TOKEN_FAILED = ErrorDef(
    code="E1005", status=502,
    message="Failed to acquire access token from Microsoft",
    fix="Check the connector app credentials and ensure the app registration is active",
)
CONNECTOR_GRAPH_UNREACHABLE = ErrorDef(
    code="E1006", status=503,
    message="Microsoft Graph API is unreachable",
    fix="Check https://status.microsoft365.com for service status",
)

# ── Auth Errors (E2xxx) ──────────────────────────────────────────

AUTH_INVALID_CREDENTIALS = ErrorDef(
    code="E2001", status=401,
    message="Invalid username or password",
    fix="Check your credentials and try again",
)
AUTH_TOKEN_EXPIRED = ErrorDef(
    code="E2002", status=401,
    message="Your session has expired",
    fix="Please log in again",
)
AUTH_ACCOUNT_DISABLED = ErrorDef(
    code="E2003", status=403,
    message="This account has been disabled",
    fix="Contact your administrator to re-enable the account",
)
AUTH_INSUFFICIENT_PERMISSIONS = ErrorDef(
    code="E2004", status=403,
    message="You don't have permission to perform this action",
    fix="Contact your administrator to request the required role",
)
AUTH_RATE_LIMITED = ErrorDef(
    code="E2005", status=429,
    message="Too many login attempts",
    fix="Wait a minute before trying again",
)

# ── Backup Errors (E3xxx) ────────────────────────────────────────

BACKUP_GRAPH_THROTTLED = ErrorDef(
    code="E3001", status=429,
    message="Microsoft Graph API is throttling requests",
    fix="Wait a few minutes — backup will auto-retry with exponential backoff",
)
BACKUP_STORAGE_FAILED = ErrorDef(
    code="E3002", status=500,
    message="Failed to write backup data to storage",
    fix="Check storage backend connectivity and available disk space",
)
BACKUP_NO_OBJECTS = ErrorDef(
    code="E3003", status=404,
    message="No objects found to back up",
    fix="Run discovery first to populate the object inventory",
)
BACKUP_ALREADY_RUNNING = ErrorDef(
    code="E3004", status=409,
    message="A backup job is already running for this scope",
    fix="Wait for the current job to complete or cancel it first",
)
BACKUP_TENANT_NOT_CONNECTED = ErrorDef(
    code="E3005", status=400,
    message="The tenant is not connected — cannot start backup",
    fix="Complete the Microsoft 365 connector setup in onboarding first",
)

# ── Recovery Errors (E4xxx) ──────────────────────────────────────

RECOVERY_NO_SNAPSHOT = ErrorDef(
    code="E4001", status=404,
    message="No backup snapshot found for the requested point-in-time",
    fix="Choose a different restore point or run a backup first",
)
RECOVERY_MALWARE_DETECTED = ErrorDef(
    code="E4002", status=422,
    message="Malware detected in backup — restore blocked",
    fix="Select a clean restore point before the infection date",
)
RECOVERY_PERMISSION_DENIED = ErrorDef(
    code="E4003", status=403,
    message="Insufficient Graph API permissions for restore",
    fix="Ensure the connector has read-write scopes and admin consent is granted",
)

# ── Storage & Infrastructure (E5xxx) ─────────────────────────────

STORAGE_UNAVAILABLE = ErrorDef(
    code="E5001", status=503,
    message="Storage backend is unavailable",
    fix="Check storage service connectivity",
)
DATABASE_ERROR = ErrorDef(
    code="E5002", status=500,
    message="Database operation failed",
    fix="Check database connectivity and try again",
)

# ── Validation (E6xxx) ───────────────────────────────────────────

VALIDATION_INVALID_INPUT = ErrorDef(
    code="E6001", status=422,
    message="Invalid input data",
    fix="Check the request body and try again",
)
VALIDATION_RESOURCE_NOT_FOUND = ErrorDef(
    code="E6002", status=404,
    message="The requested resource was not found",
    fix="Verify the resource ID and try again",
)
VALIDATION_DUPLICATE = ErrorDef(
    code="E6003", status=409,
    message="A resource with this identifier already exists",
    fix="Use a different identifier or update the existing resource",
)

# ── Rate Limiting (E7xxx) ────────────────────────────────────────

RATE_LIMIT_EXCEEDED = ErrorDef(
    code="E7001", status=429,
    message="Rate limit exceeded",
    fix="Slow down your request rate and try again",
)
