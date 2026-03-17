"""Application configuration and settings."""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "M365 Vault"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours for development

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./m365_protection.db"

    # Storage
    BACKUP_STORAGE_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    ENCRYPTION_MASTER_KEY: str = "change-me-32-byte-master-key-!!"  # Must be 32 bytes for AES-256

    # Microsoft Graph API
    MS_GRAPH_BASE_URL: str = "https://graph.microsoft.com/v1.0"
    MS_GRAPH_BATCH_URL: str = "https://graph.microsoft.com/v1.0/$batch"
    MS_AUTH_URL: str = "https://login.microsoftonline.com"
    MS_GRAPH_SCOPE: str = "https://graph.microsoft.com/.default"

    # Throttling
    GRAPH_MAX_RETRIES: int = 5
    GRAPH_RETRY_BASE_DELAY: float = 1.0
    GRAPH_MAX_CONCURRENT_REQUESTS: int = 10
    GRAPH_BATCH_SIZE: int = 20

    # Scheduler
    SCHEDULER_CHECK_INTERVAL_SECONDS: int = 60

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
