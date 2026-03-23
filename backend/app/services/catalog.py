"""Metadata catalog and search service.

Provides search across all backup snapshots — emails by subject/sender,
files by name/path, enabling fast granular recovery.
"""
import json
from typing import Optional
from datetime import datetime

from sqlalchemy import select, or_, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snapshot import Snapshot, SnapshotItem, SnapshotStatus, ItemType
from app.models.protected_object import ProtectedObject, WorkloadType


class CatalogService:
    """Search and browse backup catalog."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_emails(
        self,
        tenant_id: int,
        query: str,
        object_id: int = None,
        date_from: datetime = None,
        date_to: datetime = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Search emails across snapshots by subject, sender, or recipients."""
        stmt = (
            select(SnapshotItem, Snapshot, ProtectedObject)
            .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                ProtectedObject.workload_type == WorkloadType.EXCHANGE,
                Snapshot.status == SnapshotStatus.COMPLETED,
                SnapshotItem.item_type == ItemType.EMAIL,
                or_(
                    SnapshotItem.subject.ilike(f"%{query}%"),
                    SnapshotItem.sender.ilike(f"%{query}%"),
                    SnapshotItem.recipients.ilike(f"%{query}%"),
                    SnapshotItem.name.ilike(f"%{query}%"),
                ),
            )
        )
        if object_id:
            stmt = stmt.where(ProtectedObject.id == object_id)
        if date_from:
            stmt = stmt.where(SnapshotItem.received_at >= date_from)
        if date_to:
            stmt = stmt.where(SnapshotItem.received_at <= date_to)

        stmt = stmt.order_by(desc(SnapshotItem.received_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "item_id": item.id,
                "snapshot_id": snapshot.id,
                "object_id": obj.id,
                "object_name": obj.display_name,
                "subject": item.subject,
                "sender": item.sender,
                "recipients": item.recipients,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "size_bytes": item.size_bytes,
                "snapshot_date": snapshot.started_at.isoformat(),
                "blob_path": item.blob_path,
            }
            for item, snapshot, obj in rows
        ]

    async def search_files(
        self,
        tenant_id: int,
        query: str,
        workload_type: WorkloadType = None,
        object_id: int = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Search files across OneDrive/SharePoint snapshots by name or path."""
        stmt = (
            select(SnapshotItem, Snapshot, ProtectedObject)
            .join(Snapshot, SnapshotItem.snapshot_id == Snapshot.id)
            .join(ProtectedObject, Snapshot.protected_object_id == ProtectedObject.id)
            .where(
                ProtectedObject.tenant_id == tenant_id,
                Snapshot.status == SnapshotStatus.COMPLETED,
                SnapshotItem.item_type.in_([ItemType.FILE, ItemType.FOLDER]),
                or_(
                    SnapshotItem.name.ilike(f"%{query}%"),
                    SnapshotItem.file_name.ilike(f"%{query}%"),
                    SnapshotItem.path.ilike(f"%{query}%"),
                ),
            )
        )
        if workload_type:
            stmt = stmt.where(ProtectedObject.workload_type == workload_type)
        else:
            stmt = stmt.where(
                ProtectedObject.workload_type.in_([WorkloadType.ONEDRIVE, WorkloadType.SHAREPOINT])
            )
        if object_id:
            stmt = stmt.where(ProtectedObject.id == object_id)

        stmt = stmt.order_by(desc(SnapshotItem.last_modified_at)).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                "item_id": item.id,
                "snapshot_id": snapshot.id,
                "object_id": obj.id,
                "object_name": obj.display_name,
                "file_name": item.file_name or item.name,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "mime_type": item.mime_type,
                "last_modified": item.last_modified_at.isoformat() if item.last_modified_at else None,
                "snapshot_date": snapshot.started_at.isoformat(),
                "blob_path": item.blob_path,
                "item_type": item.item_type.value,
            }
            for item, snapshot, obj in rows
        ]

    async def search_all(
        self,
        tenant_id: int,
        query: str,
        workload_filter: str = None,
        limit: int = 50,
    ) -> dict:
        """Global search across ALL workloads — emails, files, Entra ID objects, Teams messages.

        Returns results grouped by workload with unified result format.
        """
        results = {"query": query, "total": 0, "items": []}

        # Search across all SnapshotItems matching the query
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
                    SnapshotItem.path.ilike(f"%{query}%"),
                ),
            )
        )

        if workload_filter:
            try:
                wt = WorkloadType(workload_filter)
                stmt = stmt.where(ProtectedObject.workload_type == wt)
            except ValueError:
                pass

        # Deduplicate: same ms_item_id can appear in multiple snapshots,
        # show only the latest snapshot's version
        stmt = stmt.order_by(desc(Snapshot.completed_at)).limit(limit * 2)  # Fetch extra for dedup

        result = await self.db.execute(stmt)
        rows = result.all()

        seen_items = set()
        for item, snapshot, obj in rows:
            if len(results["items"]) >= limit:
                break

            # Dedup by ms_item_id + workload
            dedup_key = f"{obj.workload_type.value}:{item.ms_item_id}"
            if dedup_key in seen_items:
                continue
            seen_items.add(dedup_key)

            workload = obj.workload_type.value
            item_data = {
                "item_id": item.id,
                "snapshot_id": snapshot.id,
                "workload": workload,
                "object_name": obj.display_name,
                "item_type": item.item_type.value,
                "name": item.name,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "blob_path": item.blob_path,
                "snapshot_date": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
            }

            # Add workload-specific fields
            if item.subject:
                item_data["subject"] = item.subject
            if item.sender:
                item_data["sender"] = item.sender
            if item.file_name:
                item_data["file_name"] = item.file_name
            if item.mime_type:
                item_data["mime_type"] = item.mime_type
            if item.received_at:
                item_data["received_at"] = item.received_at.isoformat()
            if item.last_modified_at:
                item_data["last_modified_at"] = item.last_modified_at.isoformat()
            if item.metadata_json:
                try:
                    item_data["metadata"] = json.loads(item.metadata_json)
                except (json.JSONDecodeError, TypeError):
                    pass

            results["items"].append(item_data)

        results["total"] = len(results["items"])
        return results

    async def browse_snapshot(
        self,
        snapshot_id: int,
        path: str = None,
        item_type: ItemType = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        """Browse items within a specific snapshot, optionally filtered by path."""
        stmt = (
            select(SnapshotItem)
            .where(SnapshotItem.snapshot_id == snapshot_id)
        )
        if path:
            stmt = stmt.where(SnapshotItem.path == path)
        if item_type:
            stmt = stmt.where(SnapshotItem.item_type == item_type)

        stmt = stmt.order_by(SnapshotItem.path, SnapshotItem.name).offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return [
            {
                "id": item.id,
                "item_type": item.item_type.value,
                "name": item.name,
                "path": item.path,
                "size_bytes": item.size_bytes,
                "subject": item.subject,
                "sender": item.sender,
                "file_name": item.file_name,
                "mime_type": item.mime_type,
                "received_at": item.received_at.isoformat() if item.received_at else None,
                "last_modified": item.last_modified_at.isoformat() if item.last_modified_at else None,
                "blob_path": item.blob_path,
            }
            for item in items
        ]

    async def get_snapshot_stats(self, snapshot_id: int) -> dict:
        """Get statistics for a snapshot."""
        result = await self.db.execute(
            select(
                func.count(SnapshotItem.id),
                func.sum(SnapshotItem.size_bytes),
            ).where(SnapshotItem.snapshot_id == snapshot_id)
        )
        row = result.one()
        return {
            "item_count": row[0] or 0,
            "total_size_bytes": row[1] or 0,
        }
