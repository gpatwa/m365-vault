"""Exchange backup and restore worker.

Handles backup and restore of Exchange mailbox data:
- Messages (emails) with attachments
- Calendar events
- Contacts

Uses Microsoft Graph delta queries for incremental backups.
Extends BaseWorker for parallel processing, error handling, and storage pipeline.
"""
import base64
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.workers.base_worker import BaseWorker, BackupItem

logger = logging.getLogger(__name__)


class ExchangeWorker(BaseWorker):
    """Worker for Exchange mailbox backup and restore operations.

    Discovers emails (per-folder delta), calendar events, and contacts.
    BaseWorker handles parallel processing, storage pipeline, error recording.
    """

    def workload_name(self) -> str:
        return "exchange"

    async def discover_items(
        self,
        protected_object: ProtectedObject,
        delta_token: str = None,
    ) -> tuple[list[BackupItem], Optional[str]]:
        """Discover all Exchange items: emails, calendar events, contacts.

        Returns list of BackupItems + new delta token (JSON dict of folder tokens).
        """
        user_id = protected_object.ms_object_id
        items = []

        # Parse stored delta tokens (JSON dict of folderId -> deltaLink)
        folder_tokens = self.parse_delta_tokens(delta_token)
        new_folder_tokens = {}

        # 1. Discover emails via per-folder delta queries
        email_items, new_folder_tokens = await self._discover_emails(user_id, folder_tokens)
        items.extend(email_items)

        # 2. Discover calendar events
        cal_items = await self._discover_calendar(user_id)
        items.extend(cal_items)

        # 3. Discover contacts
        contact_items = await self._discover_contacts(user_id)
        items.extend(contact_items)

        # 4. Discover attachments for emails that have them
        att_items = await self._discover_attachments(user_id, email_items)
        items.extend(att_items)

        logger.info(
            f"Exchange discovery: {len(email_items)} emails, {len(cal_items)} events, "
            f"{len(contact_items)} contacts, {len(att_items)} attachments"
        )

        return items, self.serialize_delta_tokens(new_folder_tokens)

    # ── Email Discovery ──

    async def _discover_emails(self, user_id: str, folder_tokens: dict) -> tuple[list[BackupItem], dict]:
        """Discover emails via per-folder delta queries."""
        items = []
        new_tokens = {}

        # Get mail folders
        try:
            folders = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders",
                params={"$top": "100", "$select": "id,displayName"},
            )
        except Exception as e:
            logger.error(f"Failed to list mail folders: {e}")
            folders = [
                {"id": "Inbox", "displayName": "Inbox"},
                {"id": "SentItems", "displayName": "Sent Items"},
                {"id": "Drafts", "displayName": "Drafts"},
            ]

        select_fields = "id,subject,sender,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,hasAttachments,importance,isRead,body,parentFolderId"

        for folder in folders:
            folder_id = folder.get("id")
            folder_name = folder.get("displayName", folder_id)
            existing_token = folder_tokens.get(folder_id)

            try:
                delta_path = f"/users/{user_id}/mailFolders/{folder_id}/messages/delta"

                if existing_token:
                    messages, new_delta = await self.graph.get_delta(
                        delta_path, delta_token=existing_token
                    )
                else:
                    messages, new_delta = await self.graph.get_delta(delta_path)

                if new_delta:
                    new_tokens[folder_id] = new_delta

                for msg in messages:
                    if msg.get("@removed"):
                        continue

                    sender_info = msg.get("from", {}).get("emailAddress", {})
                    received_at = msg.get("receivedDateTime")

                    items.append(BackupItem(
                        id=msg["id"],
                        item_type=ItemType.EMAIL,
                        name=msg.get("subject", "(No Subject)"),
                        path=folder_name,
                        raw_data=msg,
                        metadata={
                            "importance": msg.get("importance"),
                            "isRead": msg.get("isRead"),
                            "hasAttachments": msg.get("hasAttachments"),
                            "folderId": folder_id,
                            "folderName": folder_name,
                        },
                        extra_fields={
                            "subject": msg.get("subject", "(No Subject)"),
                            "sender": sender_info.get("address", ""),
                            "recipients": json.dumps([
                                r.get("emailAddress", {}).get("address", "")
                                for r in msg.get("toRecipients", [])
                            ]),
                            "received_at": datetime.fromisoformat(
                                received_at.replace("Z", "+00:00")
                            ).replace(tzinfo=None) if received_at else None,
                        },
                    ))

            except Exception as e:
                logger.error(f"Failed to discover folder '{folder_name}': {e}")

        return items, new_tokens

    # ── Calendar Discovery ──

    async def _discover_calendar(self, user_id: str) -> list[BackupItem]:
        """Discover calendar events."""
        items = []
        try:
            events = await self.graph.get_all_pages(
                f"/users/{user_id}/events",
                params={"$select": "id,subject,start,end,organizer,attendees,body,location,isAllDay,recurrence", "$top": "100"}
            )
            for event in events:
                items.append(BackupItem(
                    id=f"cal_{event['id']}",
                    item_type=ItemType.CALENDAR_EVENT,
                    name=event.get("subject", "(No Subject)"),
                    path="Calendar",
                    raw_data=event,
                    metadata={
                        "start": event.get("start"),
                        "end": event.get("end"),
                        "location": event.get("location", {}).get("displayName"),
                        "isAllDay": event.get("isAllDay"),
                    },
                ))
        except Exception as e:
            logger.error(f"Failed to discover calendar events: {e}")

        return items

    # ── Contact Discovery ──

    async def _discover_contacts(self, user_id: str) -> list[BackupItem]:
        """Discover contacts."""
        items = []
        try:
            contacts = await self.graph.get_all_pages(
                f"/users/{user_id}/contacts",
                params={"$select": "id,displayName,emailAddresses,businessPhones,mobilePhone,companyName,jobTitle", "$top": "100"}
            )
            for contact in contacts:
                email = None
                if contact.get("emailAddresses"):
                    email = contact["emailAddresses"][0].get("address") if contact["emailAddresses"] else None

                items.append(BackupItem(
                    id=f"contact_{contact['id']}",
                    item_type=ItemType.CONTACT,
                    name=contact.get("displayName", "Unknown"),
                    path="Contacts",
                    raw_data=contact,
                    metadata={
                        "email": email,
                        "company": contact.get("companyName"),
                        "jobTitle": contact.get("jobTitle"),
                    },
                ))
        except Exception as e:
            logger.error(f"Failed to discover contacts: {e}")

        return items

    # ── Attachment Discovery ──

    async def _discover_attachments(self, user_id: str, email_items: list[BackupItem]) -> list[BackupItem]:
        """Discover and fetch attachments for emails that have them."""
        items = []
        for email_item in email_items:
            if not email_item.metadata.get("hasAttachments"):
                continue

            msg_id = email_item.id
            try:
                attachments = await self.graph.get_all_pages(
                    f"/users/{user_id}/messages/{msg_id}/attachments"
                )
                for att in attachments:
                    content_bytes = att.get("contentBytes", "")
                    if not content_bytes:
                        continue

                    att_name = att.get("name", "attachment")
                    items.append(BackupItem(
                        id=f"{msg_id}_att_{att['id']}",
                        item_type=ItemType.FILE,
                        name=att_name,
                        path=f"attachments/{msg_id}",
                        binary_data=base64.b64decode(content_bytes),
                        mime_type=att.get("contentType", "application/octet-stream"),
                        extra_fields={
                            "file_name": att_name,
                            "content_mime_type": att.get("contentType"),
                        },
                    ))
            except Exception as e:
                logger.error(f"Failed to discover attachments for {msg_id}: {e}")

        return items

    # ═══════════════════════════════════════════════════════
    # Restore Operations (not using BaseWorker framework)
    # ═══════════════════════════════════════════════════════

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

        result = await self.db.execute(
            select(SnapshotItem).where(
                SnapshotItem.snapshot_id == snapshot.id,
                SnapshotItem.item_type == ItemType.EMAIL,
            )
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
        """Export email items as .eml file data."""
        exports = []

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
