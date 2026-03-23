"""Application configuration and settings."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "M365 Vault"
    APP_VERSION: str = "1.4.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for development

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./m365_protection.db"

    # Storage backend: "local" | "azure" | "minio"
    STORAGE_BACKEND: str = "local"
    BACKUP_STORAGE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    ENCRYPTION_MASTER_KEY: str = "change-me-32-byte-master-key-!!"  # Must be 32 bytes for AES-256

    # Azure Blob Storage (when STORAGE_BACKEND=azure)
    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_STORAGE_CONTAINER: str = "m365vault-backups"

    # MinIO / S3 (when STORAGE_BACKEND=minio)
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "m365vault-backups"
    MINIO_USE_SSL: bool = False

    # Microsoft Graph API
    MS_GRAPH_BASE_URL: str = "https://graph.microsoft.com/v1.0"
    MS_GRAPH_BATCH_URL: str = "https://graph.microsoft.com/v1.0/$batch"
    MS_AUTH_URL: str = "https://login.microsoftonline.com"
    MS_GRAPH_SCOPE: str = "https://graph.microsoft.com/.default"

    # Least-privilege Graph API scopes
    # Backup: read-only access to M365 data
    MS_GRAPH_BACKUP_SCOPES: list[str] = [
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/Calendars.Read",
        "https://graph.microsoft.com/Contacts.Read",
        "https://graph.microsoft.com/Files.Read.All",
        "https://graph.microsoft.com/Sites.Read.All",
        "https://graph.microsoft.com/User.Read.All",
        "https://graph.microsoft.com/Directory.Read.All",
        "https://graph.microsoft.com/Chat.Read.All",
        "https://graph.microsoft.com/ChannelMessage.Read.All",
        "https://graph.microsoft.com/Team.ReadBasic.All",
        "https://graph.microsoft.com/TeamSettings.Read.All",
    ]
    # Restore: read-write access to M365 data
    MS_GRAPH_RESTORE_SCOPES: list[str] = [
        "https://graph.microsoft.com/Mail.ReadWrite",
        "https://graph.microsoft.com/Calendars.ReadWrite",
        "https://graph.microsoft.com/Contacts.ReadWrite",
        "https://graph.microsoft.com/Files.ReadWrite.All",
        "https://graph.microsoft.com/Sites.ReadWrite.All",
        "https://graph.microsoft.com/User.Read.All",
        "https://graph.microsoft.com/User.ReadWrite.All",
        "https://graph.microsoft.com/Group.ReadWrite.All",
        "https://graph.microsoft.com/Application.ReadWrite.All",
        "https://graph.microsoft.com/Policy.ReadWrite.ConditionalAccess",
        "https://graph.microsoft.com/RoleManagement.ReadWrite.Directory",
    ]

    # Throttling
    GRAPH_MAX_RETRIES: int = 5
    GRAPH_RETRY_BASE_DELAY: float = 1.0
    GRAPH_MAX_CONCURRENT_REQUESTS: int = 10
    GRAPH_BATCH_SIZE: int = 20

    # Compression
    COMPRESSION_ENABLED: bool = True
    COMPRESSION_ZSTD_LEVEL_TEXT: int = 9       # High compression for JSON/text
    COMPRESSION_ZSTD_LEVEL_BINARY: int = 3     # Moderate for unknown binary
    COMPRESSION_MIN_SIZE: int = 256            # Skip compression below 256 bytes

    # Deduplication
    DEDUP_ENABLED: bool = True
    CDC_THRESHOLD_BYTES: int = 4 * 1024 * 1024   # 4 MB — files above this use CDC chunking
    CDC_TARGET_CHUNK_BYTES: int = 64 * 1024      # 64 KB target chunk size
    CDC_MIN_CHUNK_BYTES: int = 16 * 1024         # 16 KB minimum chunk
    CDC_MAX_CHUNK_BYTES: int = 256 * 1024        # 256 KB maximum chunk

    # CORS — comma-separated origins (overridden in production)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173"

    # Alerts
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    ALERT_EMAIL_RECIPIENTS: str = ""  # Comma-separated
    ALERT_WEBHOOK_URL: str = ""       # Slack, Teams, or custom webhook

    # Smart Engine
    ANOMALY_Z_SCORE_THRESHOLD: float = 2.0   # Standard deviations to flag as anomaly
    HEALTH_CHECK_INTERVAL_MINUTES: int = 5

    # Sensitive Data Scanner
    SENSITIVE_DATA_SCAN_ENABLED: bool = True

    # Malware Scanner
    MALWARE_SCAN_ON_RESTORE: bool = True

    # Backup Validation
    BACKUP_VALIDATION_ENABLED: bool = True
    VALIDATION_SAMPLE_PERCENT: int = 10

    # SSO / OIDC
    SSO_ENABLED: bool = False
    SSO_TENANT_ID: str = ""
    SSO_CLIENT_ID: str = ""
    SSO_CLIENT_SECRET: str = ""
    SSO_REDIRECT_URI: str = "http://localhost:5173/api/auth/sso/callback"

    # App Provisioning (automated onboarding)
    PROVISIONING_CLIENT_ID: str = ""      # Multi-tenant app for automated app registration
    PROVISIONING_CLIENT_SECRET: str = ""
    PROVISIONING_REDIRECT_URI: str = "http://localhost:5173/settings"

    # Scheduler
    SCHEDULER_CHECK_INTERVAL_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
