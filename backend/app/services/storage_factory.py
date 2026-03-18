"""Storage backend factory — creates the appropriate backend from config."""
import logging

from app.config import settings
from app.services.storage_backend import (
    StorageBackend,
    LocalStorageBackend,
    AzureBlobStorageBackend,
    MinIOStorageBackend,
)

logger = logging.getLogger(__name__)


def create_storage_backend() -> StorageBackend:
    """Create a storage backend based on STORAGE_BACKEND config.

    Supported values:
      - "local" (default): Filesystem storage at BACKUP_STORAGE_PATH
      - "azure": Azure Blob Storage
      - "minio": MinIO / S3-compatible storage
    """
    backend_type = settings.STORAGE_BACKEND.lower()

    if backend_type == "azure":
        if not settings.AZURE_STORAGE_CONNECTION_STRING:
            raise ValueError(
                "AZURE_STORAGE_CONNECTION_STRING is required when STORAGE_BACKEND=azure"
            )
        logger.info(
            f"Using Azure Blob Storage backend (container: {settings.AZURE_STORAGE_CONTAINER})"
        )
        return AzureBlobStorageBackend(
            connection_string=settings.AZURE_STORAGE_CONNECTION_STRING,
            container_name=settings.AZURE_STORAGE_CONTAINER,
        )

    elif backend_type in ("minio", "s3"):
        logger.info(
            f"Using MinIO/S3 storage backend (endpoint: {settings.MINIO_ENDPOINT}, "
            f"bucket: {settings.MINIO_BUCKET})"
        )
        return MinIOStorageBackend(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            bucket=settings.MINIO_BUCKET,
            use_ssl=settings.MINIO_USE_SSL,
        )

    else:
        logger.info(
            f"Using local filesystem storage backend (path: {settings.BACKUP_STORAGE_PATH})"
        )
        return LocalStorageBackend(base_path=settings.BACKUP_STORAGE_PATH)
