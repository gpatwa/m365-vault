"""Microsoft Teams backup and restore worker.

Backup strategy:
- Channel messages: Uses Export API (GET /teams/{id}/channels/getAllMessages) for
  bulk export in a single call. Falls back to per-channel delta if bulk fails.
- 1-to-1 / group chats: Uses Export API (GET /users/{id}/chats/getAllMessages)
  for per-user bulk chat export.
- Channel files: Standard drive API for file content download.
- Team settings + members: Standard team API.

Restore strategy:
- Uses Migration/Import API to recreate teams with original timestamps:
  1. Create team in migration mode
  2. Create channels in migration mode
  3. Import messages with original createdDateTime
  4. Complete migration to finalize
- Files restored via drive upload API.

All Export APIs are free (no longer metered as of Aug 2025) and do not
require the protected API form submission.
"""
import json
import logging
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.protected_object import ProtectedObject
from app.models.snapshot import Snapshot, SnapshotItem, ItemType
from app.services.graph_client import GraphClient, GraphAPIError
from app.services.storage import StorageService
from app.services.encryption import EncryptionService
from app.utils.retry import retry_async, record_failed_item

logger = logging.getLogger(__name__)

ITEM_MAX_RETRIES = 3
ITEM_BASE_DELAY = 2.0


class TeamsWorker:
    """Worker for Microsoft Teams backup and restore operations."""

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
        """Backup a Microsoft Team or user's chats.

        Returns (item_count, total_size_bytes, new_delta_token).

        Two modes based on metadata:
        - Team object (default): back up channels, messages, files, settings
        - User chats (metadata.type == "user_chats"): back up 1-to-1 and group chats
        """
        metadata = {}
        if protected_object.metadata_json:
            try:
                metadata = json.loads(protected_object.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        tokens = {}
        if delta_token:
            try:
                tokens = json.loads(delta_token)
            except (json.JSONDecodeError, TypeError):
                tokens = {}

        new_tokens = {}

        if metadata.get("type") == "user_chats":
            # Per-user chat backup
            user_id = protected_object.ms_object_id
            last_backup = tokens.get("last_backup_at")
            await self._backup_user_chats(
                user_id, protected_object, snapshot, wrapped_dek,
                since=last_backup,
            )
            new_tokens["last_backup_at"] = datetime.utcnow().isoformat()
        else:
            # Team backup
            team_id = protected_object.ms_object_id

            # 1. Channel messages via bulk Export API
            last_backup = tokens.get("last_backup_at")
            await self._backup_all_channel_messages(
                team_id, protected_object, snapshot, wrapped_dek,
                since=last_backup,
            )
            new_tokens["last_backup_at"] = datetime.utcnow().isoformat()

            # 2. Channel metadata
            await self._backup_channel_metadata(team_id, protected_object, snapshot, wrapped_dek)

            # 3. Channel files
            await self._backup_channel_files(team_id, protected_object, snapshot, wrapped_dek)

            # 4. Team settings + members
            await self._backup_team_settings(team_id, protected_object, snapshot, wrapped_dek)

        # Count totals
        result = await self.db.execute(
            select(func.count(SnapshotItem.id), func.sum(SnapshotItem.size_bytes))
            .where(SnapshotItem.snapshot_id == snapshot.id)
        )
        row = result.one()
        item_count = row[0] or 0
        total_size = row[1] or 0

        return item_count, total_size, json.dumps(new_tokens) if new_tokens else None

    # ── Helper: store a single item ──

    @retry_async(max_retries=ITEM_MAX_RETRIES, base_delay=ITEM_BASE_DELAY)
    async def _store_item(
        self, obj: dict, item_type: ItemType, ms_item_id: str,
        name: str, path: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str, metadata: dict = None,
    ):
        """Serialize, encrypt, and store a single Teams object."""
        obj_data = json.dumps(obj, default=str).encode("utf-8")
        result = await self.storage.store_item(
            tenant_id=protected_object.tenant_id,
            workload="teams",
            object_id=protected_object.ms_object_id,
            snapshot_id=snapshot.id,
            item_id=ms_item_id,
            data=obj_data,
            wrapped_dek=wrapped_dek,
            mime_type="application/json",
            db=self.db,
        )
        item = SnapshotItem(
            snapshot_id=snapshot.id,
            item_type=item_type,
            ms_item_id=ms_item_id,
            name=name,
            path=path,
            size_bytes=len(obj_data),
            compressed_size=result.compressed_size,
            content_hash=result.content_hash,
            storage_flags=result.storage_flags,
            blob_path=result.blob_path,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.db.add(item)

    # ═══════════════════════════════════════════════════════
    # BACKUP — Export APIs
    # ═══════════════════════════════════════════════════════

    # ── 1. Bulk Channel Messages (Export API) ──

    async def _backup_all_channel_messages(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str, since: str = None,
    ):
        """Backup ALL channel messages using bulk Export API.

        Uses GET /teams/{id}/channels/getAllMessages — single call for all channels.
        Falls back to per-channel queries if bulk fails.
        """
        try:
            params = {"$top": "50"}
            if since:
                params["$filter"] = f"lastModifiedDateTime gt {since}"

            messages = await self.graph.get_all_pages(
                f"/teams/{team_id}/channels/getAllMessages",
                params=params,
            )

            count = 0
            for msg in messages:
                if msg.get("@removed") or not msg.get("id"):
                    continue

                try:
                    msg_id = msg.get("id")
                    sender = "System"
                    if msg.get("from") and msg["from"].get("user"):
                        sender = msg["from"]["user"].get("displayName", "Unknown")
                    body_preview = (msg.get("body", {}).get("content", "") or "")[:100]
                    channel_id = msg.get("channelIdentity", {}).get("channelId", "")

                    await self._store_item(
                        obj=msg,
                        item_type=ItemType.CHANNEL_MESSAGE,
                        ms_item_id=msg_id,
                        name=f"{sender}: {body_preview}" if body_preview else f"Message from {sender}",
                        path=f"Channels/{channel_id[:12]}",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "sender": sender,
                            "channelId": channel_id,
                            "createdDateTime": msg.get("createdDateTime"),
                            "messageType": msg.get("messageType"),
                            "importance": msg.get("importance"),
                            "hasAttachments": bool(msg.get("attachments")),
                        },
                    )
                    count += 1
                except Exception as e:
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=msg.get("id"), item_type_str="channel_message",
                        item_name=f"Channel message", item_path="Channels",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} channel messages via bulk Export API for team {team_id}")

        except Exception as e:
            logger.warning(f"Bulk getAllMessages failed for team {team_id}: {e}, falling back to per-channel")
            await self._backup_channel_messages_fallback(team_id, protected_object, snapshot, wrapped_dek)

    async def _backup_channel_messages_fallback(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
    ):
        """Fallback: per-channel message backup using delta queries."""
        try:
            channels = await self.graph.get_all_pages(
                f"/teams/{team_id}/channels",
                params={"$select": "id,displayName"},
            )
        except Exception as e:
            logger.error(f"Failed to list channels for fallback: {e}")
            return

        for channel in channels:
            channel_id = channel.get("id")
            channel_name = channel.get("displayName", "Unknown")
            try:
                messages, _ = await self.graph.get_delta(
                    f"/teams/{team_id}/channels/{channel_id}/messages/delta"
                )
                count = 0
                for msg in messages:
                    if msg.get("@removed") or not msg.get("id"):
                        continue
                    sender = "System"
                    if msg.get("from") and msg["from"].get("user"):
                        sender = msg["from"]["user"].get("displayName", "Unknown")
                    body_preview = (msg.get("body", {}).get("content", "") or "")[:100]

                    await self._store_item(
                        obj=msg,
                        item_type=ItemType.CHANNEL_MESSAGE,
                        ms_item_id=msg["id"],
                        name=f"{sender}: {body_preview}" if body_preview else f"Message from {sender}",
                        path=f"Channels/{channel_name}",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={"sender": sender, "channelId": channel_id,
                                  "createdDateTime": msg.get("createdDateTime")},
                    )
                    count += 1
                logger.info(f"Fallback: backed up {count} messages from '{channel_name}'")
            except Exception as e:
                logger.error(f"Fallback failed for channel '{channel_name}': {e}")

        await self.db.flush()

    # ── 2. Channel Metadata ──

    async def _backup_channel_metadata(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
    ):
        """Backup channel metadata (name, description, type)."""
        try:
            channels = await self.graph.get_all_pages(
                f"/teams/{team_id}/channels",
                params={"$select": "id,displayName,description,membershipType,createdDateTime"},
            )
            for channel in channels:
                await self._store_item(
                    obj=channel,
                    item_type=ItemType.TEAM_CHANNEL,
                    ms_item_id=f"channel_{channel['id']}",
                    name=channel.get("displayName", "Unknown"),
                    path="Channels",
                    protected_object=protected_object,
                    snapshot=snapshot,
                    wrapped_dek=wrapped_dek,
                    metadata={
                        "membershipType": channel.get("membershipType"),
                        "createdDateTime": channel.get("createdDateTime"),
                    },
                )
            await self.db.flush()
            logger.info(f"Backed up {len(channels)} channel metadata for team {team_id}")
        except Exception as e:
            logger.error(f"Failed to backup channel metadata: {e}")

    # ── 3. Channel Files ──

    async def _backup_channel_files(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
    ):
        """Backup files shared in team channels."""
        try:
            channels = await self.graph.get_all_pages(
                f"/teams/{team_id}/channels",
                params={"$select": "id,displayName"},
            )
        except Exception:
            return

        for channel in channels:
            channel_id = channel.get("id")
            channel_name = channel.get("displayName", "Unknown")

            try:
                files = await self.graph.get_all_pages(
                    f"/teams/{team_id}/channels/{channel_id}/filesFolder/root/children",
                    params={"$select": "id,name,size,lastModifiedDateTime,file"},
                )
                for file_item in files:
                    if not file_item.get("file"):
                        continue  # Skip folders

                    file_id = file_item.get("id")
                    file_name = file_item.get("name", "unknown")

                    try:
                        file_data = await self.graph.get_binary(
                            f"/teams/{team_id}/channels/{channel_id}/filesFolder/root:/{file_name}:/content"
                        )
                        if not file_data:
                            continue

                        file_result = await self.storage.store_item(
                            tenant_id=protected_object.tenant_id,
                            workload="teams",
                            object_id=protected_object.ms_object_id,
                            snapshot_id=snapshot.id,
                            item_id=f"file_{file_id}",
                            data=file_data,
                            wrapped_dek=wrapped_dek,
                            filename=file_name,
                            mime_type=file_item.get("file", {}).get("mimeType"),
                            db=self.db,
                        )

                        item = SnapshotItem(
                            snapshot_id=snapshot.id,
                            item_type=ItemType.FILE,
                            ms_item_id=file_id,
                            name=file_name,
                            file_name=file_name,
                            path=f"Channels/{channel_name}/Files",
                            size_bytes=len(file_data),
                            compressed_size=file_result.compressed_size,
                            content_hash=file_result.content_hash,
                            storage_flags=file_result.storage_flags,
                            blob_path=file_result.blob_path,
                            mime_type=file_item.get("file", {}).get("mimeType"),
                            last_modified_at=datetime.fromisoformat(
                                file_item["lastModifiedDateTime"].replace("Z", "+00:00")
                            ).replace(tzinfo=None) if file_item.get("lastModifiedDateTime") else None,
                        )
                        self.db.add(item)

                    except Exception as e:
                        logger.error(f"Failed to backup file {file_name}: {e}")

            except Exception as e:
                logger.debug(f"No files folder for channel {channel_name}: {e}")

        await self.db.flush()

    # ── 4. Team Settings ──

    async def _backup_team_settings(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
    ):
        """Backup team settings, members, and metadata."""
        try:
            team = await self.graph.get(
                f"/teams/{team_id}",
                params={"$select": "id,displayName,description,visibility,memberSettings,messagingSettings,funSettings"},
            )

            members = []
            try:
                members = await self.graph.get_all_pages(
                    f"/teams/{team_id}/members",
                    params={"$select": "id,displayName,email,roles"},
                )
            except Exception:
                pass

            team_with_members = {**team, "_members": members}

            await self._store_item(
                obj=team_with_members,
                item_type=ItemType.MEETING,
                ms_item_id=f"team_settings_{team_id}",
                name=f"{team.get('displayName', 'Unknown')} (Settings)",
                path="Team Settings",
                protected_object=protected_object,
                snapshot=snapshot,
                wrapped_dek=wrapped_dek,
                metadata={
                    "visibility": team.get("visibility"),
                    "memberCount": len(members),
                },
            )

        except Exception as e:
            logger.error(f"Failed to backup team settings for {team_id}: {e}")

    # ═══════════════════════════════════════════════════════
    # BACKUP — User Chats (1-to-1 + Group)
    # ═══════════════════════════════════════════════════════

    async def _backup_user_chats(
        self, user_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str, since: str = None,
    ):
        """Backup all 1-to-1 and group chat messages for a user.

        Uses GET /users/{userId}/chats/getAllMessages (Export API).
        """
        # 1. Backup chat list (metadata)
        try:
            chats = await self.graph.get_all_pages(
                f"/users/{user_id}/chats",
                params={"$select": "id,topic,chatType,createdDateTime,lastUpdatedDateTime", "$top": "50"},
            )
            for chat in chats:
                chat_id = chat.get("id")
                chat_type = chat.get("chatType", "unknown")
                topic = chat.get("topic") or f"{chat_type} chat"

                await self._store_item(
                    obj=chat,
                    item_type=ItemType.CHAT,
                    ms_item_id=f"chat_{chat_id}",
                    name=topic,
                    path=f"Chats/{chat_type}",
                    protected_object=protected_object,
                    snapshot=snapshot,
                    wrapped_dek=wrapped_dek,
                    metadata={
                        "chatType": chat_type,
                        "createdDateTime": chat.get("createdDateTime"),
                        "lastUpdatedDateTime": chat.get("lastUpdatedDateTime"),
                    },
                )
            logger.info(f"Backed up {len(chats)} chat metadata for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to backup chat list for user {user_id}: {e}")

        # 2. Backup all chat messages via bulk Export API
        try:
            params = {"$top": "50"}
            if since:
                params["$filter"] = f"lastModifiedDateTime gt {since}"

            messages = await self.graph.get_all_pages(
                f"/users/{user_id}/chats/getAllMessages",
                params=params,
            )

            count = 0
            for msg in messages:
                if not msg.get("id"):
                    continue

                try:
                    msg_id = msg.get("id")
                    sender = "System"
                    if msg.get("from") and msg["from"].get("user"):
                        sender = msg["from"]["user"].get("displayName", "Unknown")
                    body_preview = (msg.get("body", {}).get("content", "") or "")[:100]
                    chat_id = msg.get("chatId", "")

                    await self._store_item(
                        obj=msg,
                        item_type=ItemType.CHAT_MESSAGE,
                        ms_item_id=msg_id,
                        name=f"{sender}: {body_preview}" if body_preview else f"Chat from {sender}",
                        path=f"Chats/{chat_id[:12]}",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "sender": sender,
                            "chatId": chat_id,
                            "createdDateTime": msg.get("createdDateTime"),
                            "messageType": msg.get("messageType"),
                        },
                    )
                    count += 1
                except Exception as e:
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=msg.get("id"), item_type_str="chat_message",
                        item_name=f"Chat message", item_path="Chats",
                    )

            await self.db.flush()
            logger.info(f"Backed up {count} chat messages via Export API for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to backup chat messages for user {user_id}: {e}")

    # ═══════════════════════════════════════════════════════
    # RESTORE — Migration/Import API
    # ═══════════════════════════════════════════════════════

    async def restore_items(
        self,
        item_ids: list[int],
        snapshot: Snapshot,
        wrapped_dek: str,
        target_team_id: str = None,
        protected_object: ProtectedObject = None,
    ) -> int:
        """Restore Teams items using Migration/Import API.

        For channel messages: creates a new channel in migration mode,
        imports messages with original timestamps, then completes migration.

        For files: re-uploads to channel files folder.
        """
        from sqlalchemy import select as sa_select
        target = target_team_id or (protected_object.ms_object_id if protected_object else None)
        if not target:
            logger.error("No target team ID for restore")
            return 0

        result = await self.db.execute(
            sa_select(SnapshotItem).where(SnapshotItem.id.in_(item_ids))
        )
        items = result.scalars().all()

        # Separate items by type
        messages = [i for i in items if i.item_type in (ItemType.CHANNEL_MESSAGE, ItemType.CHAT_MESSAGE)]
        files = [i for i in items if i.item_type == ItemType.FILE]

        restored = 0

        # Restore messages via migration mode
        if messages:
            restored += await self._restore_messages_via_migration(
                target, messages, snapshot, wrapped_dek
            )

        # Restore files via upload
        for item in files:
            try:
                file_data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                file_name = item.file_name or item.name

                # Find General channel for file upload
                channels = await self.graph.get_all_pages(
                    f"/teams/{target}/channels",
                    params={"$select": "id,displayName"},
                )
                general = next((c for c in channels if c["displayName"] == "General"), channels[0] if channels else None)
                if general:
                    # Get filesFolder drive
                    folder = await self.graph.get(
                        f"/teams/{target}/channels/{general['id']}/filesFolder"
                    )
                    drive_id = folder.get("parentReference", {}).get("driveId")
                    folder_id = folder.get("id")
                    if drive_id:
                        await self.graph.put(
                            f"/drives/{drive_id}/items/{folder_id}:/{file_name}:/content",
                            data=file_data,
                        )
                        restored += 1
            except Exception as e:
                logger.error(f"Failed to restore file {item.name}: {e}")

        return restored

    async def _restore_messages_via_migration(
        self, target_team_id: str, items: list[SnapshotItem],
        snapshot: Snapshot, wrapped_dek: str,
    ) -> int:
        """Restore messages using Teams Migration/Import API.

        Creates a new channel in migration mode, imports messages
        with original timestamps, then completes migration.
        """
        restored = 0

        try:
            # Create a restore channel in migration mode
            channel_name = f"Restored_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            channel_resp = await self.graph.post(
                f"/teams/{target_team_id}/channels",
                json_data={
                    "displayName": channel_name,
                    "description": f"Restored from backup snapshot {snapshot.id}",
                    "membershipType": "standard",
                    "@microsoft.graph.channelCreationMode": "migration",
                    "createdDateTime": "2020-01-01T00:00:00Z",  # Must be in past for migration
                },
            )
            channel_id = channel_resp.get("id")
            if not channel_id:
                logger.error(f"Failed to create migration channel: {channel_resp}")
                return 0

            logger.info(f"Created migration channel '{channel_name}' ({channel_id})")

            # Import messages with original timestamps
            for item in items:
                try:
                    data = await self.storage.retrieve_item(item.blob_path, wrapped_dek)
                    msg_data = json.loads(data)

                    sender = "Unknown"
                    if msg_data.get("from") and msg_data["from"].get("user"):
                        sender = msg_data["from"]["user"].get("displayName", "Unknown")

                    body = msg_data.get("body", {})
                    created = msg_data.get("createdDateTime", "2020-01-01T00:00:01Z")

                    import_body = {
                        "createdDateTime": created,
                        "from": msg_data.get("from", {
                            "user": {"id": "00000000-0000-0000-0000-000000000000",
                                     "displayName": sender, "userIdentityType": "aadUser"}
                        }),
                        "body": {
                            "contentType": body.get("contentType", "html"),
                            "content": body.get("content", f"[Restored] Message from {sender}"),
                        },
                    }

                    await self.graph.post(
                        f"/teams/{target_team_id}/channels/{channel_id}/messages",
                        json_data=import_body,
                    )
                    restored += 1

                except Exception as e:
                    logger.error(f"Failed to import message {item.ms_item_id}: {e}")

            # Complete migration
            try:
                await self.graph.post(
                    f"/teams/{target_team_id}/channels/{channel_id}/completeMigration",
                    json_data={},
                )
                logger.info(f"Migration completed for channel '{channel_name}' — {restored} messages imported")
            except Exception as e:
                logger.error(f"Failed to complete migration for channel {channel_id}: {e}")

        except Exception as e:
            logger.error(f"Migration restore failed: {e}")

        return restored
