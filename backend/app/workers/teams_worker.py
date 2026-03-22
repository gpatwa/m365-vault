"""Microsoft Teams backup worker.

Handles backup of Teams data:
- Team channels and channel messages
- Channel files (shared documents)
- Team membership and settings

Uses Microsoft Graph API with delta queries for incremental message backups.
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
    """Worker for Microsoft Teams backup operations."""

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
        """Backup a Microsoft Team.

        Returns (item_count, total_size_bytes, new_delta_token).
        Protected object ms_object_id = the Team (group) ID.
        """
        team_id = protected_object.ms_object_id

        # Parse stored delta tokens (per-channel)
        tokens = {}
        if delta_token:
            try:
                tokens = json.loads(delta_token)
            except (json.JSONDecodeError, TypeError):
                tokens = {}

        new_tokens = {}

        # 1. Backup channels and their messages
        channel_tokens = await self._backup_channels(
            team_id, protected_object, snapshot, wrapped_dek,
            channel_tokens=tokens.get("channels", {}),
        )
        if channel_tokens:
            new_tokens["channels"] = channel_tokens

        # 2. Backup channel files
        await self._backup_channel_files(team_id, protected_object, snapshot, wrapped_dek)

        # 3. Backup team settings/metadata
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

    # ── 1. Channels + Messages ──

    async def _backup_channels(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
        channel_tokens: dict = None,
    ) -> dict:
        """Backup all channels and their messages for a team."""
        channel_tokens = channel_tokens or {}
        new_tokens = {}

        try:
            channels = await self.graph.get_all_pages(
                f"/teams/{team_id}/channels",
                params={"$select": "id,displayName,description,membershipType,createdDateTime"},
            )
        except Exception as e:
            logger.error(f"Failed to list channels for team {team_id}: {e}")
            return {}

        for channel in channels:
            channel_id = channel.get("id")
            channel_name = channel.get("displayName", "Unknown Channel")

            try:
                # Store channel metadata
                await self._store_item(
                    obj=channel,
                    item_type=ItemType.TEAM_CHANNEL,
                    ms_item_id=f"channel_{channel_id}",
                    name=channel_name,
                    path="Channels",
                    protected_object=protected_object,
                    snapshot=snapshot,
                    wrapped_dek=wrapped_dek,
                    metadata={
                        "membershipType": channel.get("membershipType"),
                        "createdDateTime": channel.get("createdDateTime"),
                    },
                )

                # Backup messages in this channel
                existing_token = channel_tokens.get(channel_id)
                msg_token = await self._backup_channel_messages(
                    team_id, channel_id, channel_name,
                    protected_object, snapshot, wrapped_dek,
                    delta_token=existing_token,
                )
                if msg_token:
                    new_tokens[channel_id] = msg_token

            except Exception as e:
                logger.error(f"Failed to backup channel {channel_name}: {e}")
                await record_failed_item(
                    db=self.db, snapshot_id=snapshot.id,
                    protected_object_id=protected_object.id, error=e,
                    ms_item_id=channel_id, item_type_str="team_channel",
                    item_name=channel_name, item_path="Channels",
                )

        await self.db.flush()
        logger.info(f"Backed up {len(channels)} channels for team {team_id}")
        return new_tokens

    async def _backup_channel_messages(
        self, team_id: str, channel_id: str, channel_name: str,
        protected_object: ProtectedObject, snapshot: Snapshot,
        wrapped_dek: str, delta_token: str = None,
    ) -> str:
        """Backup messages in a channel with delta support."""
        try:
            msg_path = f"/teams/{team_id}/channels/{channel_id}/messages/delta"

            if delta_token:
                messages, new_delta = await self.graph.get_delta(
                    msg_path, delta_token=delta_token
                )
            else:
                messages, new_delta = await self.graph.get_delta(msg_path)

            count = 0
            for msg in messages:
                if msg.get("@removed"):
                    continue

                try:
                    msg_id = msg.get("id")
                    sender = msg.get("from", {}).get("user", {}).get("displayName", "Unknown")
                    body_preview = (msg.get("body", {}).get("content", "") or "")[:100]

                    await self._store_item(
                        obj=msg,
                        item_type=ItemType.CHANNEL_MESSAGE,
                        ms_item_id=msg_id,
                        name=f"{sender}: {body_preview}" if body_preview else f"Message from {sender}",
                        path=f"Channels/{channel_name}",
                        protected_object=protected_object,
                        snapshot=snapshot,
                        wrapped_dek=wrapped_dek,
                        metadata={
                            "sender": sender,
                            "createdDateTime": msg.get("createdDateTime"),
                            "messageType": msg.get("messageType"),
                            "importance": msg.get("importance"),
                        },
                    )
                    count += 1
                except Exception as e:
                    await record_failed_item(
                        db=self.db, snapshot_id=snapshot.id,
                        protected_object_id=protected_object.id, error=e,
                        ms_item_id=msg.get("id"), item_type_str="channel_message",
                        item_name=f"Message in {channel_name}", item_path=f"Channels/{channel_name}",
                    )

            logger.info(f"Backed up {count} messages from channel '{channel_name}'")
            return new_delta

        except Exception as e:
            logger.error(f"Failed to backup messages for channel {channel_name}: {e}")
            return None

    # ── 2. Channel Files ──

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
                        # Download file content
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

    # ── 3. Team Settings ──

    async def _backup_team_settings(
        self, team_id: str, protected_object: ProtectedObject,
        snapshot: Snapshot, wrapped_dek: str,
    ):
        """Backup team settings, members, and metadata."""
        try:
            # Get team details
            team = await self.graph.get(
                f"/teams/{team_id}",
                params={"$select": "id,displayName,description,visibility,memberSettings,messagingSettings,funSettings"},
            )

            # Get members
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
                item_type=ItemType.MEETING,  # Reuse for team metadata
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
