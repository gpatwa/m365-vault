"""Audit logging service — records significant operations.

Usage:
    await audit_log(db, action="backup.completed", resource_type="tenant",
                    resource_id=1, details="Backed up 42 items", user_id=1)
"""
import json
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def audit_log(
    db: AsyncSession,
    action: str,
    resource_type: str = None,
    resource_id: int = None,
    details: str = None,
    severity: str = "info",
    user_id: int = None,
    ip_address: str = None,
):
    """Write an audit log entry.

    Actions follow dot notation: category.action
    Examples: tenant.created, tenant.deactivated, tenant.purged,
              backup.started, backup.completed, backup.failed,
              restore.started, restore.completed,
              sla.assigned, sla.created, sla.deleted,
              auth.login, auth.logout,
              discovery.completed, credentials.updated
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            severity=severity,
            ip_address=ip_address,
            timestamp=datetime.utcnow(),
        )
        db.add(entry)
        await db.flush()
    except Exception as e:
        # Never let audit logging break the main operation
        logger.error(f"Failed to write audit log: {e}")
