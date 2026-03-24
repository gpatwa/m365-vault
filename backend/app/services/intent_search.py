"""Intent-aware search service for enterprise data protection.

Classifies search queries into intents and routes to appropriate
data sources. Rule-based now, LLM-ready later.

Intents:
- find_recover: Find backed-up items to restore
- status_check: Check protection/backup status of objects
- investigate: Troubleshoot failures and errors
- navigate: Go to a page or feature
- audit: View audit trail / compliance logs
- compliance: Check compliance posture (sensitive data, WORM, retention)
"""
import re
import logging
from datetime import datetime, timedelta

from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject, WorkloadType
from app.models.snapshot import SnapshotItem, Snapshot, SnapshotStatus, FailedItem, ErrorCategory
from app.models.backup_job import BackupJob, JobStatus
from app.models.audit_log import AuditLog
from app.models.health_baseline import AnomalyEvent

logger = logging.getLogger(__name__)


# ── Intent Classification ──

INTENT_PATTERNS = {
    "find_recover": {
        "keywords": ["find", "search", "where", "deleted", "lost", "restore", "recover",
                      "email", "file", "document", "message", "attachment", "download"],
        "weight": 1.0,
    },
    "status_check": {
        "keywords": ["status", "protected", "backup", "last", "check", "coverage",
                      "health", "score", "backed up", "safe", "ok"],
        "weight": 0.9,
    },
    "investigate": {
        "keywords": ["failed", "error", "why", "broken", "issue", "problem", "fix",
                      "retry", "timeout", "permission", "throttled", "crash"],
        "weight": 0.95,
    },
    "navigate": {
        "keywords": ["go to", "open", "show", "settings", "page", "dashboard", "jobs",
                      "policies", "tenants", "alerts", "reports", "audit"],
        "weight": 0.8,
    },
    "audit": {
        "keywords": ["who", "when", "changed", "modified", "audit", "history", "log",
                      "action", "user", "admin", "restored", "created"],
        "weight": 0.85,
    },
    "compliance": {
        "keywords": ["sensitive", "pii", "worm", "retention", "legal hold", "compliant",
                      "gdpr", "hipaa", "immutable", "encrypted", "security"],
        "weight": 0.9,
    },
}

NAVIGATION_LINKS = [
    {"label": "Dashboard", "path": "/", "keywords": ["dashboard", "home", "overview"]},
    {"label": "Jobs", "path": "/jobs", "keywords": ["jobs", "backup jobs", "restore jobs"]},
    {"label": "Exchange", "path": "/exchange", "keywords": ["exchange", "email", "mailbox", "calendar"]},
    {"label": "OneDrive", "path": "/onedrive", "keywords": ["onedrive", "drive", "files"]},
    {"label": "SharePoint", "path": "/sharepoint", "keywords": ["sharepoint", "sites", "lists"]},
    {"label": "Teams", "path": "/teams", "keywords": ["teams", "chat", "channels", "messages"]},
    {"label": "Entra ID", "path": "/entra-id", "keywords": ["entra", "identity", "users", "groups", "roles", "azure ad"]},
    {"label": "SLA Policies", "path": "/sla-policies", "keywords": ["sla", "policies", "schedule", "retention", "frequency"]},
    {"label": "Smart Engine", "path": "/smart-engine", "keywords": ["smart engine", "health", "anomaly", "baseline"]},
    {"label": "Alerts", "path": "/alerts", "keywords": ["alerts", "notifications", "smtp", "webhook"]},
    {"label": "Reports", "path": "/reports", "keywords": ["reports", "analytics", "performance", "storage"]},
    {"label": "Usage & License", "path": "/usage", "keywords": ["usage", "license", "tier", "billing"]},
    {"label": "Tenants", "path": "/tenants", "keywords": ["tenants", "settings", "onboard", "permissions"]},
    {"label": "Failed Items", "path": "/failed-items", "keywords": ["failed", "errors", "failures"]},
    {"label": "Audit Log", "path": "/audit", "keywords": ["audit", "log", "history", "trail"]},
    {"label": "Self Restore", "path": "/self-restore", "keywords": ["self restore", "self service", "recover my"]},
]


def classify_intent(query: str) -> list[dict]:
    """Classify a search query into ranked intents.

    Returns list of {intent, confidence} sorted by confidence desc.
    """
    query_lower = query.lower().strip()
    scores = {}

    for intent, config in INTENT_PATTERNS.items():
        score = 0
        for keyword in config["keywords"]:
            if keyword in query_lower:
                # Exact phrase match scores higher
                if " " in keyword and keyword in query_lower:
                    score += 2.0
                else:
                    score += 1.0

        if score > 0:
            scores[intent] = score * config["weight"]

    # Default to find_recover if no strong signal
    if not scores:
        scores["find_recover"] = 0.5

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: -x[1])
    return [{"intent": intent, "confidence": round(score, 2)} for intent, score in ranked]


class IntentSearchService:
    """Intent-aware search across all data sources."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search(self, query: str, tenant_id: int, workload: str = None, limit: int = 20) -> dict:
        """Execute intent-aware search.

        Returns categorized results with actions.
        """
        intents = classify_intent(query)
        primary_intent = intents[0]["intent"] if intents else "find_recover"

        results = {
            "query": query,
            "intent": primary_intent,
            "intents": intents,
            "categories": {},
            "navigation": [],
            "total": 0,
        }

        # Always check navigation links
        nav_results = self._search_navigation(query)
        if nav_results:
            results["navigation"] = nav_results

        # Route to appropriate handlers based on intent
        if primary_intent in ("find_recover", "status_check"):
            await self._search_backup_items(query, tenant_id, workload, limit, results)
            await self._search_objects(query, tenant_id, workload, results)

        if primary_intent in ("investigate", "find_recover"):
            await self._search_failed_items(query, tenant_id, results)

        if primary_intent in ("status_check",):
            await self._search_objects(query, tenant_id, workload, results)

        if primary_intent in ("audit",):
            await self._search_audit_logs(query, results)

        if primary_intent in ("investigate",):
            await self._search_anomalies(query, tenant_id, results)

        if primary_intent in ("compliance",):
            await self._search_compliance(query, tenant_id, results)

        # Count total results
        results["total"] = sum(len(cat.get("items", [])) for cat in results["categories"].values())

        return results

    def _search_navigation(self, query: str) -> list[dict]:
        """Match query against navigation links."""
        query_lower = query.lower()
        matches = []
        for link in NAVIGATION_LINKS:
            score = 0
            if query_lower in link["label"].lower():
                score = 3
            for kw in link["keywords"]:
                if kw in query_lower:
                    score = max(score, 2)
                elif query_lower in kw:
                    score = max(score, 1)
            if score > 0:
                matches.append({**link, "score": score, "type": "navigate"})
        return sorted(matches, key=lambda x: -x["score"])[:5]

    async def _search_backup_items(self, query: str, tenant_id: int,
                                    workload: str, limit: int, results: dict):
        """Search backed-up items (emails, files, chats, etc.)."""
        stmt = (
            select(SnapshotItem, Snapshot, ProtectedObject)
            .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
                or_(
                    SnapshotItem.name.ilike(f"%{query}%"),
                    SnapshotItem.subject.ilike(f"%{query}%"),
                    SnapshotItem.sender.ilike(f"%{query}%"),
                    SnapshotItem.file_name.ilike(f"%{query}%"),
                ),
            )
            .order_by(desc(Snapshot.completed_at))
            .limit(limit)
        )

        if workload:
            stmt = stmt.where(ProtectedObject.workload_type == workload)

        rows = (await self.db.execute(stmt)).all()

        items_by_type = {}
        for item, snapshot, obj in rows:
            type_key = item.item_type.value
            if type_key not in items_by_type:
                items_by_type[type_key] = []

            items_by_type[type_key].append({
                "id": item.id,
                "snapshot_id": snapshot.id,
                "type": type_key,
                "name": item.subject or item.name,
                "subtitle": item.sender or item.path or "",
                "workload": obj.workload_type.value,
                "object_name": obj.display_name,
                "size_bytes": item.size_bytes,
                "date": (snapshot.completed_at or snapshot.started_at or datetime.utcnow()).isoformat(),
                "actions": ["restore", "preview"],
            })

        # Group into categories
        TYPE_CATEGORIES = {
            "email": "Emails", "calendar_event": "Emails", "contact": "Emails",
            "file": "Files", "folder": "Files", "document_library": "Files",
            "chat_message": "Messages", "channel_message": "Messages",
            "user": "Identity", "group": "Identity", "directory_role": "Identity",
            "conditional_access_policy": "Configuration", "app_registration": "Configuration",
            "named_location": "Configuration", "role_assignment": "Configuration",
        }

        for type_key, items in items_by_type.items():
            category = TYPE_CATEGORIES.get(type_key, "Other")
            if category not in results["categories"]:
                results["categories"][category] = {"items": [], "icon": category.lower()}
            results["categories"][category]["items"].extend(items)

    async def _search_objects(self, query: str, tenant_id: int, workload: str, results: dict):
        """Search protected objects (mailboxes, sites, teams, etc.)."""
        stmt = select(ProtectedObject).where(
            ProtectedObject.tenant_id == tenant_id,
            ProtectedObject.display_name.ilike(f"%{query}%"),
        )
        if workload:
            stmt = stmt.where(ProtectedObject.workload_type == workload)
        stmt = stmt.limit(10)

        rows = (await self.db.execute(stmt)).scalars().all()

        if rows:
            results["categories"]["Protected Objects"] = {
                "icon": "objects",
                "items": [
                    {
                        "id": obj.id,
                        "type": "object",
                        "name": obj.display_name,
                        "subtitle": f"{obj.workload_type.value} • {obj.status.value}",
                        "workload": obj.workload_type.value,
                        "status": obj.status.value,
                        "last_backup": obj.last_backup_at.isoformat() if obj.last_backup_at else None,
                        "actions": ["view", "backup"],
                    }
                    for obj in rows
                ],
            }

    async def _search_failed_items(self, query: str, tenant_id: int, results: dict):
        """Search failed items for troubleshooting."""
        stmt = (
            select(FailedItem, ProtectedObject)
            .join(ProtectedObject, FailedItem.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                FailedItem.is_resolved == False,
                or_(
                    FailedItem.item_name.ilike(f"%{query}%"),
                    FailedItem.error_message.ilike(f"%{query}%"),
                ),
            )
            .order_by(desc(FailedItem.created_at))
            .limit(10)
        )
        rows = (await self.db.execute(stmt)).all()

        if rows:
            results["categories"]["Failures"] = {
                "icon": "failures",
                "items": [
                    {
                        "id": fi.id,
                        "type": "failed_item",
                        "name": fi.item_name or "Unknown item",
                        "subtitle": f"{fi.error_category} — {(fi.error_message or '')[:80]}",
                        "workload": obj.workload_type.value,
                        "can_retry": fi.can_retry,
                        "resolution": fi.resolution_hint,
                        "actions": ["retry", "dismiss"] if fi.can_retry else ["dismiss"],
                    }
                    for fi, obj in rows
                ],
            }

    async def _search_audit_logs(self, query: str, results: dict):
        """Search audit logs."""
        stmt = (
            select(AuditLog)
            .where(or_(
                AuditLog.action.ilike(f"%{query}%"),
                AuditLog.details.ilike(f"%{query}%"),
                AuditLog.resource_type.ilike(f"%{query}%"),
            ))
            .order_by(desc(AuditLog.timestamp))
            .limit(10)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        if rows:
            results["categories"]["Audit Trail"] = {
                "icon": "audit",
                "items": [
                    {
                        "id": log.id,
                        "type": "audit_log",
                        "name": log.action,
                        "subtitle": f"{log.resource_type} • {log.details[:60] if log.details else ''}",
                        "date": log.timestamp.isoformat() if log.timestamp else None,
                        "severity": log.severity,
                        "actions": ["view"],
                    }
                    for log in rows
                ],
            }

    async def _search_anomalies(self, query: str, tenant_id: int, results: dict):
        """Search anomaly events."""
        stmt = (
            select(AnomalyEvent)
            .where(
                AnomalyEvent.tenant_id == tenant_id,
                or_(
                    AnomalyEvent.message.ilike(f"%{query}%"),
                    AnomalyEvent.workload_type.ilike(f"%{query}%"),
                    AnomalyEvent.metric_name.ilike(f"%{query}%"),
                ),
            )
            .order_by(desc(AnomalyEvent.detected_at))
            .limit(10)
        )
        rows = (await self.db.execute(stmt)).scalars().all()

        if rows:
            results["categories"]["Anomalies"] = {
                "icon": "anomalies",
                "items": [
                    {
                        "id": a.id,
                        "type": "anomaly",
                        "name": f"{a.workload_type} — {a.metric_name}",
                        "subtitle": a.message[:80] if a.message else "",
                        "severity": a.severity,
                        "z_score": a.z_score,
                        "resolved": bool(a.resolved),
                        "actions": ["investigate"],
                    }
                    for a in rows
                ],
            }

    async def _search_compliance(self, query: str, tenant_id: int, results: dict):
        """Search compliance-related data."""
        # Check for sensitive data findings, WORM status, etc.
        # For now, return navigation links to compliance-related pages
        results["categories"]["Compliance"] = {
            "icon": "compliance",
            "items": [
                {"type": "link", "name": "Sensitive Data Scan Results", "path": "/reports", "actions": ["view"]},
                {"type": "link", "name": "WORM & Legal Hold Status", "path": "/sla-policies", "actions": ["view"]},
                {"type": "link", "name": "Backup Validation Results", "path": "/reports", "actions": ["view"]},
                {"type": "link", "name": "Compliance Report", "path": "/reports", "actions": ["view"]},
            ],
        }
