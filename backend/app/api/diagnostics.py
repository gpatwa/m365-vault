"""Diagnostics API — admin-only system health and troubleshooting.

Provides real-time visibility into every critical dependency so issues
are diagnosed instantly, not through trial-and-error debugging.
"""
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.services.auth import require_backup_permission
from app.services.system_health import SystemHealthService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagnostics", tags=["Diagnostics"])


@router.get("/health")
async def full_health_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Comprehensive system health check — tests every dependency.

    Returns structured report with:
    - Each check: name, healthy/unhealthy, detail, fix action, latency
    - Overall score (e.g., "6/7 passed")
    - Critical failures with exact remediation steps
    """
    service = SystemHealthService(db)
    return await service.run_all_checks()


@router.get("/connector-test")
async def test_connector(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Test M365 connector secret against Azure AD.

    This is the pre-flight check that runs BEFORE redirecting users to Microsoft.
    If this fails, the onboarding "Connect" button should show an error instead
    of sending the user to Microsoft only to fail on callback.
    """
    from app.config import settings
    import msal

    app_id = settings.CONNECTOR_APP_ID
    secret = settings.CONNECTOR_APP_SECRET

    if not app_id or not secret:
        return {
            "status": "not_configured",
            "message": "M365 connector credentials not set",
            "fix": "Set CONNECTOR_APP_ID and CONNECTOR_APP_SECRET environment variables",
        }

    # Test token acquisition
    results = []
    for authority_label, authority_url in [
        ("common", "https://login.microsoftonline.com/common"),
        ("organizations", "https://login.microsoftonline.com/organizations"),
    ]:
        start = time.time()
        try:
            msal_app = msal.ConfidentialClientApplication(
                client_id=app_id,
                client_credential=secret,
                authority=authority_url,
            )
            token = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            latency = int((time.time() - start) * 1000)

            if "access_token" in token:
                results.append({"authority": authority_label, "status": "ok", "latency_ms": latency})
            else:
                error = token.get("error_description", token.get("error", "unknown"))
                # Classify the error
                if "AADSTS7000215" in error:
                    status = "invalid_secret"
                elif "AADSTS7000229" in error:
                    status = "no_sp_ok"  # Normal for multi-tenant
                elif "AADSTS53003" in error:
                    status = "conditional_access_blocked"
                else:
                    status = "error"
                results.append({
                    "authority": authority_label, "status": status,
                    "error": error[:200], "latency_ms": latency
                })
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            results.append({
                "authority": authority_label, "status": "exception",
                "error": str(e)[:200], "latency_ms": latency
            })

    # Determine overall status
    any_ok = any(r["status"] in ("ok", "no_sp_ok") for r in results)
    any_invalid = any(r["status"] == "invalid_secret" for r in results)

    if any_invalid:
        overall = "invalid_secret"
        message = ("The client secret is INVALID. Azure AD rejected it. "
                   "Create a new secret in Azure Portal > App Registrations > "
                   f"{app_id} > Certificates & Secrets, then update CONNECTOR_APP_SECRET.")
    elif any_ok:
        overall = "healthy"
        message = "Connector secret is valid. Ready for customer onboarding."
    else:
        overall = "degraded"
        message = "Could not validate secret (may be conditional access or network issue)."

    return {
        "status": overall,
        "message": message,
        "app_id": app_id,
        "secret_configured": bool(secret),
        "secret_length": len(secret) if secret else 0,
        "results": results,
        "tested_at": datetime.utcnow().isoformat(),
    }


@router.get("/msal-test")
async def test_msal_direct(
    tenant_id: str = "9e0cfba8-9047-4240-97bf-9cb024db4971",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Run MSAL token acquisition from INSIDE the container — definitive test.

    This runs the exact same code path as the OAuth callback connector.
    If this works but the callback fails, the issue is in the callback flow.
    If this fails too, the issue is the secret/environment.
    """
    from app.config import settings
    import msal

    app_id = settings.CONNECTOR_APP_ID
    secret = settings.CONNECTOR_APP_SECRET

    if not app_id or not secret:
        return {"status": "not_configured"}

    results = {}

    # Test 1: Raw MSAL with explicit secret
    start = time.time()
    try:
        msal_app = msal.ConfidentialClientApplication(
            client_id=app_id,
            client_credential=secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        token = msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        latency = int((time.time() - start) * 1000)

        if "access_token" in token:
            results["msal_direct"] = {"status": "ok", "latency_ms": latency}
        else:
            results["msal_direct"] = {
                "status": "fail",
                "error": token.get("error_description", "")[:200],
                "latency_ms": latency,
            }
    except Exception as e:
        results["msal_direct"] = {"status": "exception", "error": str(e)[:200]}

    # Test 2: Via connector (same path as callback)
    start = time.time()
    try:
        from app.connectors.registry import get_connector
        connector = get_connector("microsoft365")
        # Simulate what handle_callback does
        msal_app2 = msal.ConfidentialClientApplication(
            client_id=connector.app_id,
            client_credential=connector.app_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        token2 = msal_app2.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        latency = int((time.time() - start) * 1000)

        if "access_token" in token2:
            results["via_connector"] = {"status": "ok", "latency_ms": latency}
        else:
            results["via_connector"] = {
                "status": "fail",
                "error": token2.get("error_description", "")[:200],
                "latency_ms": latency,
            }
    except Exception as e:
        results["via_connector"] = {"status": "exception", "error": str(e)[:200]}

    # Debug info
    results["debug"] = {
        "settings_app_id": app_id,
        "settings_secret_configured": bool(secret),
        "settings_secret_len": len(secret) if secret else 0,
        "connector_app_id": connector.app_id if 'connector' in dir() else None,
        "connector_secret_configured": bool(connector.app_secret) if 'connector' in dir() else None,
        "connector_secret_len": len(connector.app_secret) if 'connector' in dir() and connector.app_secret else 0,
        "secrets_configured": bool(secret) and bool(connector.app_secret if 'connector' in dir() else None),
        "target_tenant": tenant_id,
    }

    return results


@router.get("/graph-metrics")
async def get_graph_metrics(
    tenant_id: str = None,
    window: int = 300,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Graph API call metrics — per-tenant, per-workload.

    Shows API call volume, throttle rate, latency, and budget utilization.
    Use this to monitor Microsoft Graph API consumption and detect throttling.

    Args:
        tenant_id: Filter to specific tenant (MS tenant ID). None = all tenants.
        window: Time window in seconds (default: 300 = last 5 min).
    """
    from app.services.graph_client import graph_metrics

    if tenant_id:
        return graph_metrics.get_stats(tenant_id, window)

    # All tenants
    tenants = graph_metrics.get_all_tenants()
    if not tenants:
        return {
            "message": "No Graph API calls recorded yet. Metrics start tracking when backups or discovery runs.",
            "tenants": [],
        }

    return {
        "tenants": [
            graph_metrics.get_stats(t, window)
            for t in tenants
        ],
    }


@router.get("/performance")
async def get_performance_metrics(
    tenant_id: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """System performance metrics — API latency, backup throughput, resource usage.

    Provides baseline numbers for benchmarking and SLA tracking.
    """
    from sqlalchemy import func, select
    from app.models.backup_job import BackupJob, JobStatus
    from app.models.restore_job import RestoreJob, RestoreStatus
    from app.models.snapshot import Snapshot, SnapshotStatus
    from app.models.protected_object import ProtectedObject
    from app.services.graph_client import graph_metrics

    now = datetime.utcnow()
    since_24h = now - __import__('datetime').timedelta(hours=24)
    since_7d = now - __import__('datetime').timedelta(days=7)

    # Backup throughput (last 24h)
    backup_stmt = select(BackupJob).where(
        BackupJob.status == JobStatus.COMPLETED,
        BackupJob.completed_at >= since_24h,
    )
    if tenant_id:
        backup_stmt = backup_stmt.where(BackupJob.tenant_id == tenant_id)

    backup_jobs = (await db.execute(backup_stmt)).scalars().all()

    total_items_backed_up = sum(j.total_items or 0 for j in backup_jobs)
    total_size_backed_up = sum(j.total_size_bytes or 0 for j in backup_jobs)
    total_backup_duration = sum(
        (j.completed_at - j.started_at).total_seconds()
        for j in backup_jobs
        if j.completed_at and j.started_at
    )

    # Restore performance (last 7d)
    restore_stmt = select(RestoreJob).where(
        RestoreJob.status == RestoreStatus.COMPLETED,
        RestoreJob.completed_at >= since_7d,
    )
    if tenant_id:
        restore_stmt = restore_stmt.where(RestoreJob.tenant_id == tenant_id)
    restore_jobs = (await db.execute(restore_stmt)).scalars().all()

    # Snapshot stats
    snap_stmt = select(
        func.count(),
        func.sum(Snapshot.size_bytes),
        func.sum(Snapshot.item_count),
    ).where(Snapshot.status == SnapshotStatus.COMPLETED)
    snap_result = await db.execute(snap_stmt)
    snap_row = snap_result.one()

    # Graph API stats (all tenants)
    graph_all = {}
    for t in graph_metrics.get_all_tenants():
        stats = graph_metrics.get_stats(t, 3600)  # Last hour
        if stats["total_calls"] > 0:
            graph_all[t] = stats

    return {
        "backup_24h": {
            "jobs_completed": len(backup_jobs),
            "total_items": total_items_backed_up,
            "total_size_bytes": total_size_backed_up,
            "total_duration_seconds": round(total_backup_duration),
            "items_per_minute": round(total_items_backed_up / (total_backup_duration / 60)) if total_backup_duration > 0 else 0,
            "mb_per_second": round(total_size_backed_up / total_backup_duration / 1024 / 1024, 2) if total_backup_duration > 0 else 0,
        },
        "restore_7d": {
            "jobs_completed": len(restore_jobs),
            "avg_duration_seconds": round(
                sum((j.completed_at - j.started_at).total_seconds() for j in restore_jobs if j.completed_at and j.started_at) / len(restore_jobs)
            ) if restore_jobs else 0,
        },
        "snapshots": {
            "total_count": snap_row[0] or 0,
            "total_size_bytes": snap_row[1] or 0,
            "total_items": snap_row[2] or 0,
        },
        "graph_api": graph_all if graph_all else {"message": "No Graph API calls in the last hour"},
    }


@router.get("/env")
async def show_environment(
    current_user: User = Depends(require_backup_permission),
):
    """Show non-sensitive environment configuration for debugging."""
    from app.config import settings
    return {
        "storage_backend": settings.STORAGE_BACKEND,
        "cors_origins": settings.CORS_ORIGINS,
        "dispatch_mode": getattr(settings, "DISPATCH_MODE", "in_process"),
        "rate_limit": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        "connector_app_id": settings.CONNECTOR_APP_ID or "(not set)",
        "connector_secret_set": bool(settings.CONNECTOR_APP_SECRET),
        "connector_secret_length": len(settings.CONNECTOR_APP_SECRET) if settings.CONNECTOR_APP_SECRET else 0,
        "connector_secret_configured": bool(settings.CONNECTOR_APP_SECRET),
        "database_url_set": bool(settings.DATABASE_URL),
        "encryption_key_set": bool(settings.ENCRYPTION_MASTER_KEY),
        "debug": getattr(settings, "DEBUG", False),
    }


@router.get("/circuit-breaker")
async def circuit_breaker_status(
    current_user: User = Depends(require_backup_permission),
    db: AsyncSession = Depends(get_db),
):
    """Show circuit breaker state for all known tenants.

    Returns per-tenant state (open/closed), failure rate, and cooldown remaining.
    """
    from app.services.circuit_breaker import circuit_breaker
    from app.models.tenant import Tenant
    from sqlalchemy import select

    result = await db.execute(select(Tenant))
    tenants = result.scalars().all()

    statuses = {}
    for tenant in tenants:
        status = circuit_breaker.get_status(tenant.ms_tenant_id or str(tenant.id))
        statuses[tenant.name] = {
            "tenant_id": tenant.id,
            "ms_tenant_id": tenant.ms_tenant_id,
            **status,
        }

    open_count = sum(1 for s in statuses.values() if s["state"] == "open")
    return {
        "summary": {
            "total_tenants": len(statuses),
            "circuits_open": open_count,
            "circuits_closed": len(statuses) - open_count,
        },
        "tenants": statuses,
        "config": {
            "failure_threshold": circuit_breaker.threshold,
            "window_seconds": circuit_breaker.window,
            "cooldown_seconds": circuit_breaker.cooldown,
            "min_calls": circuit_breaker.min_calls,
        },
    }


@router.get("/resilience")
async def resilience_overview(
    current_user: User = Depends(require_backup_permission),
):
    """Overview of all resilience mechanisms and their current state."""
    from app.services.circuit_breaker import circuit_breaker
    from app.services.resilience import idempotency_store
    from app.config import settings

    return {
        "circuit_breaker": {
            "enabled": True,
            "threshold": circuit_breaker.threshold,
            "window_seconds": circuit_breaker.window,
            "cooldown_seconds": circuit_breaker.cooldown,
        },
        "retry": {
            "graph_max_retries": settings.GRAPH_MAX_RETRIES,
            "graph_retry_base_delay": settings.GRAPH_RETRY_BASE_DELAY,
        },
        "idempotency": {
            "enabled": True,
            "cache_size": len(idempotency_store._store),
            "default_ttl_seconds": idempotency_store._default_ttl,
        },
        "rate_limiting": {
            "default_rpm": settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
            "auth_rpm": 20,
            "onboard_rpm": 60,
        },
        "concurrency": {
            "graph_max_concurrent": settings.GRAPH_MAX_CONCURRENT_REQUESTS,
            "worker_concurrency": settings.WORKER_CONCURRENCY,
            "item_concurrency": settings.ITEM_CONCURRENCY,
        },
    }


@router.get("/secrets")
async def get_secret_diagnostics(
    current_user: User = Depends(require_backup_permission),
):
    """Secret expiry status for all SaaS workload apps.

    Returns status (healthy/warning/critical/expired) without
    exposing actual secret values. Used for operational monitoring.
    """
    from app.services.secret_rotation import get_secret_status
    return await get_secret_status()


@router.post("/cleanup-stale-data")
async def cleanup_stale_data(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_backup_permission),
):
    """Remove stale data from pre-launch era: dead-lettered jobs, internal
    failed items, and resolved anomalies. Admin-only.

    Safe for pre-launch environments with no customers. Removes:
    - Dead-lettered backup jobs (internal failures, not recoverable)
    - Failed items with internal error messages (sqlalchemy, asyncpg, etc.)
    - Resolved anomaly events (already cleaned up)
    - All remaining active anomaly events (mark resolved)
    """
    from sqlalchemy import text

    results = {}

    # 1. Delete dead-lettered backup jobs
    r = await db.execute(text("DELETE FROM backup_jobs WHERE status::text = 'dead_letter'"))
    results["dead_letter_jobs_deleted"] = r.rowcount

    # 2. Delete internal failed items
    r = await db.execute(text("""
        DELETE FROM failed_items
        WHERE error_message ILIKE '%sqlalchemy%'
           OR error_message ILIKE '%concurrent operations%'
           OR error_message ILIKE '%session is provisioning%'
           OR error_message ILIKE '%asyncpg%'
           OR error_message ILIKE '%no active connection%'
           OR error_category::text = 'internal_transient'
    """))
    results["internal_failed_items_deleted"] = r.rowcount

    # 3. Delete resolved anomalies
    r = await db.execute(text("DELETE FROM anomaly_events WHERE resolved = 1"))
    results["resolved_anomalies_deleted"] = r.rowcount

    # 4. Resolve all remaining stale anomalies
    r = await db.execute(text("UPDATE anomaly_events SET resolved = 1 WHERE resolved = 0"))
    results["stale_anomalies_resolved"] = r.rowcount

    await db.commit()

    import logging
    logging.getLogger(__name__).info(f"Stale data cleanup: {results}")

    return {"status": "cleaned", **results}
