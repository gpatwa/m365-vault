"""Snapshot, SnapshotItem, and FailedItem models — point-in-time backup records."""
import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Text, ForeignKey, Boolean
from app.database import Base


class SnapshotType(str, enum.Enum):
    FULL = "full"
    INCREMENTAL = "incremental"


class SnapshotStatus(str, enum.Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    protected_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=False, index=True)
    snapshot_type = Column(Enum(SnapshotType), nullable=False)
    status = Column(Enum(SnapshotStatus), default=SnapshotStatus.IN_PROGRESS, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    size_bytes = Column(Integer, default=0)
    item_count = Column(Integer, default=0)
    delta_token = Column(Text, nullable=True)  # MS Graph delta token for incremental
    blob_path = Column(String(1000), nullable=True)  # Path to encrypted blob on disk
    encryption_key_id = Column(String(255), nullable=True)  # DEK reference
    error_message = Column(Text, nullable=True)
    items_failed = Column(Integer, default=0)      # Count of items that failed during backup
    items_skipped = Column(Integer, default=0)      # Count of items intentionally skipped
    locked_until = Column(DateTime, nullable=True)  # WORM: immutable until this date
    validation_status = Column(String(50), nullable=True)  # passed/failed/partial
    validated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ItemType(str, enum.Enum):
    EMAIL = "email"
    CALENDAR_EVENT = "calendar_event"
    CONTACT = "contact"
    FILE = "file"
    FOLDER = "folder"
    LIST = "list"
    LIST_ITEM = "list_item"
    DOCUMENT_LIBRARY = "document_library"
    # Entra ID object types
    USER = "user"
    GROUP = "group"
    DIRECTORY_ROLE = "directory_role"
    ROLE_ASSIGNMENT = "role_assignment"
    CONDITIONAL_ACCESS_POLICY = "conditional_access_policy"
    APP_REGISTRATION = "app_registration"
    NAMED_LOCATION = "named_location"
    SERVICE_PRINCIPAL = "service_principal"
    ADMINISTRATIVE_UNIT = "administrative_unit"
    OAUTH_PERMISSION_GRANT = "oauth_permission_grant"
    DEVICE = "device"
    DOMAIN = "domain"
    # Phase 2/3: New object types
    MAIL_RULE = "mail_rule"                        # Exchange inbox rules
    PIM_ELIGIBILITY = "pim_eligibility"            # PIM eligible role assignments
    PIM_ASSIGNMENT = "pim_assignment"              # PIM active role assignments
    CONFIG = "config"                              # Generic configuration items
    # Teams object types
    CHAT_MESSAGE = "chat_message"
    CHANNEL_MESSAGE = "channel_message"
    TEAM_CHANNEL = "team_channel"
    MEETING = "meeting"
    CHAT = "chat"                      # Chat metadata (1-to-1 or group)
    CHAT_ATTACHMENT = "chat_attachment" # File attached to chat message


class SnapshotItem(Base):
    __tablename__ = "snapshot_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False, index=True)
    item_type = Column(Enum(ItemType), nullable=False)
    ms_item_id = Column(String(255), nullable=False, index=True)  # Graph API item ID
    name = Column(String(1000), nullable=False)
    path = Column(String(2000), nullable=True)  # Folder path or mailbox folder
    size_bytes = Column(Integer, default=0)
    compressed_size = Column(Integer, nullable=True)    # Size after compression (before encryption)
    content_hash = Column(String(255), nullable=True)   # SHA-256 of compressed data (for dedup)
    storage_flags = Column(Integer, default=0)          # Bit 0=compressed, 1=chunked, 2=deduped
    blob_path = Column(String(1000), nullable=True)     # Path to item blob on disk
    metadata_json = Column(Text, nullable=True)         # Item-specific metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Email-specific fields
    subject = Column(String(1000), nullable=True)
    sender = Column(String(500), nullable=True)
    recipients = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=True)

    # File-specific fields
    file_name = Column(String(500), nullable=True)
    mime_type = Column(String(255), nullable=True)
    last_modified_at = Column(DateTime, nullable=True)


class ErrorCategory(str, enum.Enum):
    """Categorizes failed item errors for actionable resolution guidance."""
    PERMISSION_DENIED = "permission_denied"          # 403 — tenant needs to grant Graph API permission
    NOT_FOUND = "not_found"                          # 404 — item was deleted in M365 since discovery
    THROTTLED = "throttled"                          # 429 — exhausted all retries under throttling
    TIMEOUT = "timeout"                              # Request timed out after retries
    QUOTA_EXCEEDED = "quota_exceeded"                # Storage or API quota hit
    FILE_TOO_LARGE = "file_too_large"                # File exceeds max size for Graph download
    ENCRYPTION_ERROR = "encryption_error"            # DEK/encryption failure on our side
    STORAGE_ERROR = "storage_error"                  # Could not write to backup storage
    INVALID_DATA = "invalid_data"                    # Malformed Graph API response
    AUTH_EXPIRED = "auth_expired"                    # 401 — token/credentials expired
    SERVER_ERROR = "server_error"                    # 5xx from Graph
    NETWORK_ERROR = "network_error"                  # Connection/DNS failure
    UNKNOWN = "unknown"                              # Unclassified


# Human-readable resolution guidance per error category
ERROR_RESOLUTION_GUIDE = {
    ErrorCategory.PERMISSION_DENIED: "Grant the required Microsoft Graph API permission in Azure AD → App Registrations → API Permissions.",
    ErrorCategory.NOT_FOUND: "The item was deleted or moved in Microsoft 365. No action needed — it will be excluded from future backups.",
    ErrorCategory.THROTTLED: "Microsoft Graph API rate limit was exceeded. The item will be retried automatically in the next backup cycle.",
    ErrorCategory.TIMEOUT: "The request timed out. This is usually transient — retry the item or wait for the next scheduled backup.",
    ErrorCategory.QUOTA_EXCEEDED: "API or storage quota reached. Check Azure subscription limits or increase backup storage capacity.",
    ErrorCategory.FILE_TOO_LARGE: "File exceeds the 4 MB direct download limit. Consider enabling large-file upload sessions in settings.",
    ErrorCategory.ENCRYPTION_ERROR: "Encryption key issue. Verify the master key configuration and ensure the DEK is not corrupted.",
    ErrorCategory.STORAGE_ERROR: "Could not write to backup storage. Check disk space, file permissions, and storage path configuration.",
    ErrorCategory.INVALID_DATA: "Microsoft Graph returned malformed data. This is usually transient — retry the item.",
    ErrorCategory.AUTH_EXPIRED: "Authentication credentials expired. Re-authenticate the tenant in Settings → Tenants → Edit.",
    ErrorCategory.SERVER_ERROR: "Microsoft Graph returned a server error (5xx). This is transient — retry the item.",
    ErrorCategory.NETWORK_ERROR: "Network connectivity issue. Check DNS resolution and outbound HTTPS access to graph.microsoft.com.",
    ErrorCategory.UNKNOWN: "Unclassified error. Check the error message for details and retry if appropriate.",
}


class FailedItem(Base):
    """Records items that failed during a backup snapshot.

    Provides visibility into exactly which items were skipped, why,
    and what action the tenant admin can take to fix it.
    """
    __tablename__ = "failed_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("snapshots.id"), nullable=False, index=True)
    protected_object_id = Column(Integer, ForeignKey("protected_objects.id"), nullable=False, index=True)

    # Item identification
    ms_item_id = Column(String(255), nullable=True)   # Graph API item ID (if known)
    item_type = Column(Enum(ItemType), nullable=True)  # email, file, folder, etc.
    item_name = Column(String(1000), nullable=True)    # Display name / subject
    item_path = Column(String(2000), nullable=True)    # Folder path or mailbox folder

    # Error details
    error_category = Column(Enum(ErrorCategory), default=ErrorCategory.UNKNOWN, nullable=False)
    error_message = Column(Text, nullable=False)       # Full error message
    error_code = Column(String(100), nullable=True)    # Graph error code (e.g., "ErrorItemNotFound")
    http_status = Column(Integer, nullable=True)       # HTTP status code if applicable
    retries_attempted = Column(Integer, default=0)     # How many retries were attempted

    # Resolution
    resolution_hint = Column(Text, nullable=True)      # Human-readable fix suggestion
    is_resolved = Column(Boolean, default=False)       # Admin marked as resolved / acknowledged
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(255), nullable=True)   # Username who resolved

    # Retry tracking
    can_retry = Column(Boolean, default=True)          # Whether this item can be retried
    retry_snapshot_id = Column(Integer, nullable=True)  # Snapshot ID where retry succeeded

    created_at = Column(DateTime, default=datetime.utcnow)
