"""Application configuration and settings."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "KavachIQ"
    APP_VERSION: str = "3.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour (production-safe default)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

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

    # HTTPS
    FORCE_HTTPS: bool = False  # Set True in production (Azure Container Apps)

    # Rate Limiting (tiered: auth=20/min, onboard=60/min, API=600/min. 0 = disabled)
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 600  # Default for authenticated API endpoints

    # Logging
    LOG_FORMAT: str = "text"  # "text" for dev, "json" for production

    # Password Policy
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True

    # Refresh Tokens
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Demo Mode
    DEMO_MODE: bool = False  # Auto-seed demo data on startup if DB is empty

    # License — Option B pricing: community (free), professional ($1.50), business ($3), enterprise ($5)
    LICENSE_TIER: str = "community"  # community, professional, business, enterprise
    LICENSE_MAX_USERS: int = 25      # for community tier

    # Feature overrides — force enable/disable features regardless of tier
    # Format: "+msp_dashboard,-worm,+org_context"  (+ enables, - disables)
    FEATURE_OVERRIDES: str = ""

    # Session Management (BFF pattern — httpOnly cookies + Redis)
    SESSION_TTL_HOURS: int = 24                  # Redis session TTL (default 24 hours)
    COOKIE_DOMAIN: str = ""                       # Cookie domain (empty = same origin, ".kavachiq.com" for prod)
    BACKEND_URL: str = "http://localhost:8000"    # Backend URL for OAuth callback redirect_uri

    # Multi-tenant Connector (OAuth onboarding)
    CONNECTOR_APP_ID: str = ""        # KavachIQ Connector multi-tenant app ID
    CONNECTOR_APP_SECRET: str = ""    # KavachIQ Connector app secret
    CONNECTOR_REDIRECT_URI: str = "http://localhost:8000/api/onboard/callback"  # Backend URL (BFF pattern)

    # Dispatcher (Control Plane / Data Plane separation)
    DISPATCH_MODE: str = "redis"  # "redis" (production) | "in_process" (dev without Redis)
    REDIS_URL: str = "redis://localhost:6379/0"
    WORKER_CONCURRENCY: int = 3        # Async tasks per worker process
    ITEM_CONCURRENCY: int = 10         # Items processed in parallel per object

    # Fault Tolerance
    JOB_TIMEOUT_MINUTES: int = 60           # Stale job detection threshold
    CIRCUIT_BREAKER_THRESHOLD: float = 0.5  # 50% failure rate triggers circuit
    CIRCUIT_BREAKER_WINDOW: int = 300       # 5-minute window
    CIRCUIT_BREAKER_COOLDOWN: int = 900     # 15-minute cooldown

    # Alerts
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    ALERT_EMAIL_RECIPIENTS: str = ""  # Comma-separated
    ALERT_WEBHOOK_URL: str = ""       # Slack, Teams, or custom webhook

    # Email (transactional)
    EMAIL_PROVIDER: str = "console"  # console, resend, smtp
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "KavachIQ <noreply@kavachiq.com>"
    FRONTEND_URL: str = "http://localhost:5173"

    # Stripe Billing
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_PRICE_PROFESSIONAL: str = ""
    STRIPE_PRICE_BUSINESS: str = ""
    STRIPE_PRICE_ENTERPRISE: str = ""
    TRIAL_PERIOD_DAYS: int = 14

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
    BATCH_THRESHOLD: int = 500       # Objects per workload before splitting into batches
    BATCH_SIZE: int = 500            # Objects per child batch job

    # Anomaly Detection
    ANOMALY_MAX_PER_TENANT: int = 10  # Max active anomalies per tenant (ceiling)
    ANOMALY_RESOLVE_AFTER_DAYS: int = 30  # Auto-resolve unresolved anomalies older than this
    ANOMALY_DELETE_AFTER_DAYS: int = 90   # Delete resolved anomalies older than this

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False  # Allow both STRIPE_SECRET_KEY and stripe_secret_key
        extra = "ignore"  # Allow extra env vars (M365 credentials in .env)


settings = Settings()

# Startup security validation — reject insecure defaults in production
INSECURE_DEFAULTS = ["change-me", "docker-dev-secret", "docker-dev-32"]

def validate_production_config():
    """Warn or block if insecure defaults are used in production (DEBUG=False)."""
    import logging
    _log = logging.getLogger("config")
    issues = []
    if any(d in settings.SECRET_KEY for d in INSECURE_DEFAULTS):
        issues.append("SECRET_KEY is using an insecure default — generate with: openssl rand -hex 32")
    if any(d in settings.ENCRYPTION_MASTER_KEY for d in INSECURE_DEFAULTS):
        issues.append("ENCRYPTION_MASTER_KEY is using an insecure default — generate with: openssl rand -hex 32")
    if issues:
        if not settings.DEBUG:
            for issue in issues:
                _log.critical(f"SECURITY: {issue}")
            raise RuntimeError("Production deployment with insecure defaults. Set SECRET_KEY and ENCRYPTION_MASTER_KEY.")
        else:
            for issue in issues:
                _log.warning(f"DEV MODE: {issue}")

validate_production_config()
