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

        # 5. Discover archive mailbox emails (Professional+ feature)
        archive_items = await self._discover_archive(user_id, folder_tokens, new_folder_tokens)
        items.extend(archive_items)

        # 6. Discover mail rules (Professional+ feature)
        rule_items = await self._discover_mail_rules(user_id)
        items.extend(rule_items)

        # 7. Discover public folder emails (Professional+ feature)
        pub_items = await self._discover_public_folders(user_id, folder_tokens, new_folder_tokens)
        items.extend(pub_items)

        # 8. Discover journal mailbox (Enterprise feature)
        journal_items = await self._discover_journal(user_id, folder_tokens, new_folder_tokens)
        items.extend(journal_items)

        logger.info(
            f"Exchange discovery: {len(email_items)} emails, {len(cal_items)} events, "
            f"{len(contact_items)} contacts, {len(att_items)} attachments, {len(rule_items)} rules, "
            f"{len(pub_items)} public folder items, {len(journal_items)} journal items"
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

    # ── Archive Mailbox Discovery (Professional+) ──

    async def _discover_archive(self, user_id: str, folder_tokens: dict, new_folder_tokens: dict) -> list[BackupItem]:
        """Discover emails in archive mailbox. Feature-gated to Professional+."""
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("archive_mailbox"):
            return []

        items = []
        try:
            # Check if archive folder exists
            archive_folders = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders",
                params={"$select": "id,displayName,totalItemCount", "$top": "50", "includeHiddenFolders": "true"},
            )
            archive_folder = next((f for f in archive_folders if f.get("displayName") == "Archive"), None)
            if not archive_folder:
                return []

            archive_id = archive_folder["id"]
            total = archive_folder.get("totalItemCount", 0)
            if total == 0:
                return []

            # Delta sync archive folder
            token_key = f"archive_{archive_id}"
            existing_token = folder_tokens.get(token_key)
            delta_path = f"/users/{user_id}/mailFolders/{archive_id}/messages/delta"

            try:
                if existing_token:
                    messages, new_delta = await self.graph.get_delta(delta_path, delta_token=existing_token)
                else:
                    messages = await self.graph.get_all_pages(
                        f"/users/{user_id}/mailFolders/{archive_id}/messages",
                        params={
                            "$select": "id,subject,sender,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments,importance,isRead",
                            "$top": "200",
                        },
                    )
                    new_delta = None
            except Exception:
                messages = []
                new_delta = None

            if new_delta:
                new_folder_tokens[token_key] = new_delta

            for msg in messages:
                if msg.get("@removed"):
                    continue
                items.append(BackupItem(
                    id=f"archive_{msg['id']}",
                    item_type="email",
                    name=msg.get("subject", "(No Subject)"),
                    path="Archive",
                    raw_data=msg,
                    metadata={
                        "importance": msg.get("importance"),
                        "isRead": msg.get("isRead"),
                        "hasAttachments": msg.get("hasAttachments"),
                        "folderId": archive_id,
                        "folderName": "Archive",
                        "isArchive": True,
                    },
                    extra_fields={
                        "subject": msg.get("subject"),
                        "sender": msg.get("sender", {}).get("emailAddress", {}).get("address"),
                        "received_at": msg.get("receivedDateTime"),
                    },
                ))

            if items:
                logger.info(f"Discovered {len(items)} archive emails for {user_id}")
        except Exception as e:
            logger.warning(f"Archive mailbox discovery failed for {user_id}: {e}")

        return items

    # ── Mail Rules Discovery (Professional+) ──

    async def _discover_mail_rules(self, user_id: str) -> list[BackupItem]:
        """Discover inbox mail rules for a user. Feature-gated to Professional+."""
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("mail_rules_backup"):
            return []

        items = []
        try:
            rules = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders/inbox/messageRules",
                params={"$top": "100"},
            )
            for rule in rules:
                rule_name = rule.get("displayName", f"Rule {rule.get('id', 'unknown')}")
                items.append(BackupItem(
                    id=f"rule_{rule['id']}",
                    item_type="mail_rule",
                    name=rule_name,
                    path="MailRules",
                    raw_data=rule,
                    metadata={
                        "isEnabled": rule.get("isEnabled", False),
                        "sequence": rule.get("sequence"),
                        "hasActions": bool(rule.get("actions")),
                        "hasConditions": bool(rule.get("conditions")),
                    },
                ))
            if rules:
                logger.info(f"Discovered {len(rules)} mail rules for {user_id}")
        except Exception as e:
            logger.warning(f"Mail rules discovery failed for {user_id}: {e}")

        return items

    # ── Mail Rules Restore ──

    async def restore_mail_rules(self, user_id: str, rules: list[dict]) -> int:
        """Restore inbox mail rules for a user."""
        restored = 0
        for rule_data in rules:
            try:
                # Strip read-only fields
                payload = {k: v for k, v in rule_data.items()
                          if k not in ("id", "@odata.type", "@odata.context")}
                payload["displayName"] = f"[Restored] {payload.get('displayName', 'Rule')}"
                await self.graph.post(
                    f"/users/{user_id}/mailFolders/inbox/messageRules",
                    json=payload,
                )
                restored += 1
            except Exception as e:
                logger.error(f"Failed to restore mail rule: {e}")
        return restored

    # ── Public Folders Discovery (Professional+) ──

    async def _discover_public_folders(self, user_id: str, folder_tokens: dict, new_folder_tokens: dict) -> list[BackupItem]:
        """Discover emails in public folders. Feature-gated to Professional+.

        Public folders are organizational mailbox folders shared across the tenant.
        Uses the same delta pattern as archive/inbox backup.
        """
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("public_folder"):
            return []

        items = []
        try:
            # Get all mail folders including hidden/public
            all_folders = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders",
                params={
                    "$select": "id,displayName,totalItemCount,parentFolderId,childFolderCount",
                    "$top": "100",
                    "includeHiddenFolders": "true",
                },
            )

            # Find root public folder and its children
            pub_root = next((f for f in all_folders if f.get("displayName", "").lower() in ("public folders", "publicfolders")), None)
            if not pub_root:
                return []

            pub_root_id = pub_root["id"]

            # Get child folders under the public folder root
            pub_children = await self.graph.get_all_pages(
                f"/users/{user_id}/mailFolders/{pub_root_id}/childFolders",
                params={"$select": "id,displayName,totalItemCount", "$top": "100"},
            )

            for folder in pub_children:
                folder_id = folder["id"]
                folder_name = folder.get("displayName", "Public Folder")
                total = folder.get("totalItemCount", 0)
                if total == 0:
                    continue

                # Delta sync per public folder
                token_key = f"public_{folder_id}"
                existing_token = folder_tokens.get(token_key)
                delta_path = f"/users/{user_id}/mailFolders/{folder_id}/messages/delta"

                try:
                    if existing_token:
                        messages, new_delta = await self.graph.get_delta(delta_path, delta_token=existing_token)
                    else:
                        messages = await self.graph.get_all_pages(
                            f"/users/{user_id}/mailFolders/{folder_id}/messages",
                            params={
                                "$select": "id,subject,sender,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments,importance",
                                "$top": "200",
                            },
                        )
                        new_delta = None
                except Exception:
                    messages = []
                    new_delta = None

                if new_delta:
                    new_folder_tokens[token_key] = new_delta

                for msg in messages:
                    if msg.get("@removed"):
                        continue
                    items.append(BackupItem(
                        id=f"public_{msg['id']}",
                        item_type="email",
                        name=msg.get("subject", "(No Subject)"),
                        path=f"PublicFolders/{folder_name}",
                        raw_data=msg,
                        metadata={
                            "importance": msg.get("importance"),
                            "hasAttachments": msg.get("hasAttachments"),
                            "folderId": folder_id,
                            "folderName": folder_name,
                            "isPublicFolder": True,
                        },
                        extra_fields={
                            "subject": msg.get("subject"),
                            "sender": msg.get("sender", {}).get("emailAddress", {}).get("address"),
                            "received_at": msg.get("receivedDateTime"),
                        },
                    ))

            if items:
                logger.info(f"Discovered {len(items)} public folder emails for {user_id}")
        except Exception as e:
            logger.warning(f"Public folder discovery failed for {user_id}: {e}")

        return items

    # ── Journal Mailbox Discovery (Enterprise) ──

    async def _discover_journal(self, user_id: str, folder_tokens: dict, new_folder_tokens: dict) -> list[BackupItem]:
        """Discover journal mailbox entries. Feature-gated to Enterprise.

        Journal mailboxes receive copies of all tenant email per compliance rules.
        The journal mailbox is a special system mailbox — we look for it by
        checking the organization's journal rules config.
        """
        from app.services.feature_flags import feature_flags
        if not feature_flags.is_enabled("journal_mailbox"):
            return []

        items = []
        try:
            # Check if this user IS the journal mailbox (metadata flag from discovery)
            # Journal mailbox is identified during tenant discovery and tagged
            if not getattr(self, '_is_journal_mailbox', False):
                return []

            # Delta sync the journal mailbox inbox
            token_key = "journal_inbox"
            existing_token = folder_tokens.get(token_key)
            delta_path = f"/users/{user_id}/mailFolders/inbox/messages/delta"

            try:
                if existing_token:
                    messages, new_delta = await self.graph.get_delta(delta_path, delta_token=existing_token)
                else:
                    messages = await self.graph.get_all_pages(
                        f"/users/{user_id}/mailFolders/inbox/messages",
                        params={
                            "$select": "id,subject,sender,from,toRecipients,receivedDateTime,bodyPreview,hasAttachments",
                            "$top": "200",
                        },
                    )
                    new_delta = None
            except Exception:
                messages = []
                new_delta = None

            if new_delta:
                new_folder_tokens[token_key] = new_delta

            for msg in messages:
                if msg.get("@removed"):
                    continue
                items.append(BackupItem(
                    id=f"journal_{msg['id']}",
                    item_type="email",
                    name=msg.get("subject", "(Journal Entry)"),
                    path="JournalMailbox",
                    raw_data=msg,
                    metadata={
                        "hasAttachments": msg.get("hasAttachments"),
                        "isJournalEntry": True,
                    },
                    extra_fields={
                        "subject": msg.get("subject"),
                        "sender": msg.get("sender", {}).get("emailAddress", {}).get("address"),
                        "received_at": msg.get("receivedDateTime"),
                    },
                ))

            if items:
                logger.info(f"Discovered {len(items)} journal entries for {user_id}")
        except Exception as e:
            logger.warning(f"Journal mailbox discovery failed for {user_id}: {e}")

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
        """Export email items as RFC 2822 compliant .eml files.

        Converts stored Graph API JSON to proper .eml format with
        headers, body (HTML + plain text), and MIME attachments.
        Uses Python stdlib email module — no external dependencies.
        """
        from email.message import EmailMessage
        from email.utils import formatdate, formataddr
        from datetime import datetime as _dt
        import base64 as _b64

        exports = []

        result = await self.db.execute(
            select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        for item in items:
            try:
                raw = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                msg_data = json.loads(raw) if isinstance(raw, (str, bytes)) else raw

                # Build RFC 2822 email
                eml = EmailMessage()

                # Headers
                subject = msg_data.get("subject", "(No Subject)")
                eml["Subject"] = subject

                sender = msg_data.get("from", {}).get("emailAddress", {})
                if sender:
                    eml["From"] = formataddr((sender.get("name", ""), sender.get("address", "")))

                to_list = msg_data.get("toRecipients", [])
                if to_list:
                    eml["To"] = ", ".join(
                        formataddr((r.get("emailAddress", {}).get("name", ""), r.get("emailAddress", {}).get("address", "")))
                        for r in to_list
                    )

                cc_list = msg_data.get("ccRecipients", [])
                if cc_list:
                    eml["Cc"] = ", ".join(
                        formataddr((r.get("emailAddress", {}).get("name", ""), r.get("emailAddress", {}).get("address", "")))
                        for r in cc_list
                    )

                received = msg_data.get("receivedDateTime")
                if received:
                    try:
                        dt = _dt.fromisoformat(received.replace("Z", "+00:00"))
                        eml["Date"] = formatdate(dt.timestamp(), localtime=False)
                    except Exception:
                        eml["Date"] = received

                eml["Message-ID"] = f"<{msg_data.get('internetMessageId', item.ms_item_id)}>"
                eml["X-KavachIQ-Backup"] = f"snapshot={snapshot.id} item={item.id}"

                # Body (prefer HTML, fall back to plain text)
                body = msg_data.get("body", {})
                body_content = body.get("content", "")
                body_type = body.get("contentType", "text")

                if body_type == "html":
                    eml.set_content(body_content, subtype="html")
                else:
                    eml.set_content(body_content)

                # Attachments (if stored inline in the backup)
                attachments = msg_data.get("attachments", [])
                for att in attachments:
                    att_name = att.get("name", "attachment")
                    att_content_type = att.get("contentType", "application/octet-stream")
                    att_bytes = att.get("contentBytes")
                    if att_bytes:
                        try:
                            decoded = _b64.b64decode(att_bytes)
                            maintype, _, subtype = att_content_type.partition("/")
                            eml.add_attachment(decoded, maintype=maintype, subtype=subtype or "octet-stream", filename=att_name)
                        except Exception:
                            pass  # Skip malformed attachments

                # Generate filename
                safe_subject = "".join(c if c.isalnum() or c in " -_" else "_" for c in subject)[:50]
                filename = f"{safe_subject}_{item.ms_item_id[:8]}.eml"

                exports.append({
                    "filename": filename,
                    "data": eml.as_bytes(),
                    "size": len(eml.as_bytes()),
                    "subject": subject,
                    "path": item.path or "Inbox",
                })
            except Exception as e:
                logger.error(f"Failed to export item {item.id} to .eml: {e}")

        return exports
