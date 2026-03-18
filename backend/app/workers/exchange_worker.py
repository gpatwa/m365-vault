"""Exchange backup and restore worker.

Handles backup and restore of Exchange mailbox data:
- Messages (emails) with attachments
- Calendar events
- Contacts

Uses Microsoft Graph delta queries for incremental backups.
"""
import json
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient, GraphAPIError
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.utils.retry import retry_async, record_failed_item

logger = logging.getLogger(__name__)

# Item-level retry config: 3 retries with 2s base delay
ITEM_MAX_RETRIES = 3
ITEM_BASE_DELAY = 2.0


class ExchangeWorker:
    """Worker for Exchange mailbox backup and restore operations."""

    def __init__(
        self,
        db: AsyncSession,
        graph: GraphClient,
        storage: StorageService,
        encryption: EncryptionService,
    ):
        self.db = db
        self.graph = graph
        self.storage = storage
        self.encryption = encryption

    async def backup(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> tuple[int, int, str]:
        """Backup an Exchange mailbox.

        Returns (item_count, total_size_bytes, new_delta_token).
        """
        user_id = protected_object.ms_object_id
        item_count = 0
        total_size = 0

        # Backup emails using delta query
        new_delta_token = await self._backup_messages(
            user_id=user_id,
            protected_object=protected_object,
            snapshot=snapshot,
            wrapped_dek=wrapped_dek,
            delta_token=delta_token,
        )

        # Count items
        from sqlalchemy import select, func
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        item_count = row[0] or 0
        total_size = row[1] or 0

        # Backup calendar events
        await self._backup_calendar(user_id, protected_object, snapshot, wrapped_dek)

        # Backup contacts
        await self._backup_contacts(user_id, protected_object, snapshot, wrapped_dek)

        # Recount
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        item_count = row[0] or 0
        total_size = row[1] or 0

        return item_count, total_size, new_delta_token

    async def _backup_messages(
        self,
        user_id: str,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        delta_token: str = None,
    ) -> str:
        """Backup email messages using per-folder delta queries.

        Graph API supports delta queries for messages only at the folder level:
          /users/{id}/mailFolders/{folderId}/messages/delta
        NOT at the top-level /users/{id}/messages/delta.

        For full backup: discover all mail folders, then delta-sync each one.
        For incremental: use stored delta tokens (JSON dict keyed by folder ID).
        """
        select_fields = "id,subject,sender,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,hasAttachments,importance,isRead,body,parentFolderId"

        # Parse stored delta tokens (JSON dict of folderId -> deltaLink)
        folder_tokens = {}
        if delta_token:
            try:
                folder_tokens = json.loads(delta_token)
            except (json.JSONDecodeError, TypeError):
                folder_tokens = {}

        # Discover all mail folders for this user
        try:
            folders = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders",
                params={"$top": "100", "$select": "id,displayName"},
            )
        except Exception as e:
            logger.error(f"Failed to list mail folders for user {user_id}: {e}")
            folders = []

        # If no folders found, fall back to well-known folders
        if not folders:
            folders = [
                {"id": "Inbox", "displayName": "Inbox"},
                {"id": "SentItems", "displayName": "Sent Items"},
                {"id": "Drafts", "displayName": "Drafts"},
            ]

        new_folder_tokens = {}

        for folder in folders:
            folder_id = folder.get("id")
            folder_name = folder.get("displayName", folder_id)
            existing_token = folder_tokens.get(folder_id)

            try:
                delta_path = f"/users/{user_id}/mailFolders/{folder_id}/messages/delta"
                params = {"$select": select_fields}

                if existing_token:
                    # Incremental: use the stored deltaLink URL
                    messages, new_delta = await self.graph.get_delta(
                        delta_path, delta_token=existing_token
                    )
                else:
                    # Full sync for this folder
                    messages, new_delta = await self.graph.get_delta(delta_path)

                if new_delta:
                    new_folder_tokens[folder_id] = new_delta

                for msg in messages:
                    try:
                        # Skip deleted items in delta response
                        if msg.get("@removed"):
                            continue

                        await self._backup_single_message(
                            msg=msg,
                            folder_id=folder_id,
                            folder_name=folder_name,
                            user_id=user_id,
                            protected_object=protected_object,
                            snapshot=snapshot,
                            wrapped_dek=wrapped_dek,
                        )

                    except Exception as e:
                        logger.error(f"Failed to backup message {msg.get('id')} after retries: {e}")
                        await record_failed_item(
                            db=self.db,
                            snapshot_id=snapshot.id,
                            protected_object_id=protected_object.id,
                            error=e,
                            ms_item_id=msg.get("id"),
                            item_type_str="email",
                            item_name=msg.get("subject", "(No Subject)"),
                            item_path=folder_name,
                            retries_attempted=ITEM_MAX_RETRIES,
                        )

                logger.info(f"Backed up {len(messages)} messages from folder '{folder_name}'")

            except Exception as e:
                logger.error(f"Failed to backup folder '{folder_name}' ({folder_id}): {e}")

        await self.db.flush()
        # Return delta tokens as JSON string for all folders
        return json.dumps(new_folder_tokens) if new_folder_tokens else None

    @retry_async(max_retries=ITEM_MAX_RETRIES, base_delay=ITEM_BASE_DELAY)
    async def _backup_single_message(
        self,
        msg: dict,
        folder_id: str,
        folder_name: str,
        user_id: str,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
    ):
        """Backup a single email message with retry support."""
        msg_id = msg.get("id")
        subject = msg.get("subject", "(No Subject)")
        sender_info = msg.get("from", {}).get("emailAddress", {})
        sender = sender_info.get("address", "")
        recipients = json.dumps([
            r.get("emailAddress", {}).get("address", "")
            for r in msg.get("toRecipients", [])
        ])
        received_at = msg.get("receivedDateTime")

        # Serialize full message as JSON for storage
        msg_data = json.dumps(msg, default=str).encode("utf-8")

        # Store through compression/dedup/encryption pipeline
        result = await self.storage.store_item(
            tenant_id=protected_object.tenant_id,
            workload="exchange",
            object_id=protected_object.ms_object_id,
            snapshot_id=snapshot.id,
            item_id=msg_id,
            data=msg_data,
            wrapped_dek=wrapped_dek,
            mime_type="application/json",
            db=self.db,
        )

        # Create catalog entry
        item = SnapshotItem(
            snapshot_id=snapshot.id,
            item_type=ItemType.EMAIL,
            ms_item_id=msg_id,
            name=subject,
            path=folder_name,
            size_bytes=len(msg_data),
            compressed_size=result.compressed_size,
            content_hash=result.content_hash,
            storage_flags=result.storage_flags,
            blob_path=result.blob_path,
            subject=subject,
            sender=sender,
            recipients=recipients,
            received_at=datetime.fromisoformat(received_at.replace("Z", "+00:00")).replace(tzinfo=None) if received_at else None,
            metadata_json=json.dumps({
                "importance": msg.get("importance"),
                "isRead": msg.get("isRead"),
                "hasAttachments": msg.get("hasAttachments"),
                "folderId": folder_id,
                "folderName": folder_name,
            }),
        )
        self.db.add(item)

        # Backup attachments if present
        if msg.get("hasAttachments"):
            await self._backup_attachments(
                user_id, msg_id, protected_object, snapshot, wrapped_dek
            )

    async def _backup_attachments(
        self, user_id: str, message_id: str,
        protected_object: ProtectedObject, snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup attachments for a specific email message."""
        try:
            attachments = await self.graph.get_all_pages(
                f"/users/{user_id}/messages/{message_id}/attachments"
            )
            for att in attachments:
                att_id = att.get("id")
                att_name = att.get("name", "attachment")
                content_bytes = att.get("contentBytes", "")

                if content_bytes:
                    import base64
                    att_data = base64.b64decode(content_bytes)

                    att_result = await self.storage.store_item(
                        tenant_id=protected_object.tenant_id,
                        workload="exchange",
                        object_id=protected_object.ms_object_id,
                        snapshot_id=snapshot.id,
                        item_id=f"{message_id}_att_{att_id}",
                        data=att_data,
                        wrapped_dek=wrapped_dek,
                        filename=att_name,
                        mime_type=att.get("contentType"),
                        db=self.db,
                    )

                    item = SnapshotItem(
                        snapshot_id=snapshot.id,
                        item_type=ItemType.FILE,
                        ms_item_id=att_id,
                        name=att_name,
                        file_name=att_name,
                        path=f"attachments/{message_id}",
                        size_bytes=len(att_data),
                        compressed_size=att_result.compressed_size,
                        content_hash=att_result.content_hash,
                        storage_flags=att_result.storage_flags,
                        mime_type=att.get("contentType"),
                        blob_path=att_result.blob_path,
                    )
                    self.db.add(item)

        except Exception as e:
            logger.error(f"Failed to backup attachments for message {message_id}: {e}")

    async def _backup_calendar(
        self, user_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup calendar events."""
        try:
            events = await self.graph.get_all_pages(
                f"/users/{user_id}/events",
                params={"$select": "id,subject,start,end,organizer,attendees,body,location,isAllDay,recurrence", "$top": "100"}
            )
            for event in events:
                try:
                    event_id = event.get("id")
                    event_data = json.dumps(event, default=str).encode("utf-8")

                    evt_result = await self.storage.store_item(
                        tenant_id=protected_object.tenant_id,
                        workload="exchange",
                        object_id=protected_object.ms_object_id,
                        snapshot_id=snapshot.id,
                        item_id=f"cal_{event_id}",
                        data=event_data,
                        wrapped_dek=wrapped_dek,
                        mime_type="application/json",
                        db=self.db,
                    )

                    item = SnapshotItem(
                        snapshot_id=snapshot.id,
                        item_type=ItemType.CALENDAR_EVENT,
                        ms_item_id=event_id,
                        name=event.get("subject", "(No Subject)"),
                        path="Calendar",
                        size_bytes=len(event_data),
                        compressed_size=evt_result.compressed_size,
                        content_hash=evt_result.content_hash,
                        storage_flags=evt_result.storage_flags,
                        blob_path=evt_result.blob_path,
                        metadata_json=json.dumps({
                            "start": event.get("start"),
                            "end": event.get("end"),
                            "location": event.get("location", {}).get("displayName"),
                            "isAllDay": event.get("isAllDay"),
                        }),
                    )
                    self.db.add(item)
                except Exception as e:
                    logger.error(f"Failed to backup calendar event {event.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=event.get("id"), item_type_str="calendar_event",
                        item_name=event.get("subject", "(No Subject)"), item_path="Calendar",
                    )

        except Exception as e:
            logger.error(f"Failed to backup calendar for user {user_id}: {e}")

    async def _backup_contacts(
        self, user_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str
    ):
        """Backup contacts."""
        try:
            contacts = await self.graph.get_all_pages(
                f"/users/{user_id}/contacts",
                params={"$select": "id,displayName,emailAddresses,businessPhones,mobilePhone,companyName,jobTitle", "$top": "100"}
            )
            for contact in contacts:
                try:
                    contact_id = contact.get("id")
                    contact_data = json.dumps(contact, default=str).encode("utf-8")

                    ct_result = await self.storage.store_item(
                        tenant_id=protected_object.tenant_id,
                        workload="exchange",
                        object_id=protected_object.ms_object_id,
                        snapshot_id=snapshot.id,
                        item_id=f"contact_{contact_id}",
                        data=contact_data,
                        wrapped_dek=wrapped_dek,
                        mime_type="application/json",
                        db=self.db,
                    )

                    item = SnapshotItem(
                        snapshot_id=snapshot.id,
                        item_type=ItemType.CONTACT,
                        ms_item_id=contact_id,
                        name=contact.get("displayName", "Unknown"),
                        path="Contacts",
                        size_bytes=len(contact_data),
                        compressed_size=ct_result.compressed_size,
                        content_hash=ct_result.content_hash,
                        storage_flags=ct_result.storage_flags,
                        blob_path=ct_result.blob_path,
                        metadata_json=json.dumps({
                            "email": (contact.get("emailAddresses") or [{}])[0].get("address") if contact.get("emailAddresses") else None,
                            "company": contact.get("companyName"),
                            "jobTitle": contact.get("jobTitle"),
                        }),
                    )
                    self.db.add(item)
                except Exception as e:
                    logger.error(f"Failed to backup contact {contact.get('id')}: {e}")
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=contact.get("id"), item_type_str="contact",
                        item_name=contact.get("displayName", "Unknown"), item_path="Contacts",
                    )

        except Exception as e:
            logger.error(f"Failed to backup contacts for user {user_id}: {e}")

    async def restore_full_mailbox(
        self,
        protected_object: ProtectedObject,
        snapshot: Snapshot,
        wrapped_dek: str,
        target_user_id: str = None,
    ) -> int:
        """Restore entire mailbox from snapshot to original or different user."""
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        from sqlalchemy import select
        result = await self.db.execute(
            select(SnapshotItem).where(
                SnapshotItem.snapshot_id == snapshot.id,
                SnapshotItem.item_type == ItemType.EMAIL,
            )
        )
        items = result.scalars().all()

        for item in items:
            try:
                # Retrieve and decrypt the email data
                data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                msg_data = json.loads(data)

                # Restore via Graph API — create message in target mailbox
                restore_body = {
                    "subject": msg_data.get("subject"),
                    "body": msg_data.get("body"),
                    "toRecipients": msg_data.get("toRecipients", []),
                    "ccRecipients": msg_data.get("ccRecipients", []),
                }

                await self.graph.post(f"/users/{target}/messages", json_data=restore_body)
                items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore email {item.ms_item_id}: {e}")

        return items_restored

    async def restore_items(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
        target_user_id: str = None,
        protected_object: ProtectedObject = None,
    ) -> int:
        """Restore specific email items."""
        target = target_user_id or protected_object.ms_object_id
        items_restored = 0

        from sqlalchemy import select
        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        for item in items:
            try:
                data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                msg_data = json.loads(data)

                restore_body = {
                    "subject": msg_data.get("subject"),
                    "body": msg_data.get("body"),
                    "toRecipients": msg_data.get("toRecipients", []),
                }
                await self.graph.post(f"/users/{target}/messages", json_data=restore_body)
                items_restored += 1

            except Exception as e:
                logger.error(f"Failed to restore item {item.id}: {e}")

        return items_restored

    async def export_to_eml(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
    ) -> list[dict]:
        """Export email items as .eml file data. Returns list of {filename, data}."""
        exports = []

        from sqlalchemy import select
        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        for item in items:
            try:
                data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                filename = f"{item.subject or 'email'}_{item.ms_item_id[:8]}.eml"
                exports.append({"filename": filename, "data": data})
            except Exception as e:
                logger.error(f"Failed to export item {item.id}: {e}")

        return exports
