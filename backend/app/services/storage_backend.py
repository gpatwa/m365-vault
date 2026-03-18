"""Pluggable storage backend abstraction.

Provides a uniform interface for blob storage across:
- Local filesystem (bare-metal dev, default)
- Azure Blob Storage (production on Azure)
- MinIO / S3 (Docker Compose local dev, AWS production)

All paths are forward-slash delimited keys (e.g. "1/exchange/user-id/1/items/msg.blob").
The backend translates these to the underlying storage system.
"""
import logging
import os
import shutil
from abc import ABC, abstractmethod
from typing import Optional

import aiofiles

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract blob storage interface.

    All methods use forward-slash delimited string keys.
    Implementations handle path translation for their storage system.
    """

    @abstractmethod
    async def write(self, key: str, data: bytes) -> None:
        """Write data to a storage key. Creates parent dirs/prefixes as needed."""

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """Read data from a storage key. Raises FileNotFoundError if missing."""

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a single key. Returns True if deleted, False if not found."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a key exists."""

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """Delete all keys under a prefix (like rm -rf). Returns count deleted."""

    @abstractmethod
    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""


# ═══════════════════════════════════════════════════════════════════════════
#  Local Filesystem Backend
# ═══════════════════════════════════════════════════════════════════════════

class LocalStorageBackend(StorageBackend):
    """Filesystem-based storage. Keys map to file paths under base_path.

    This is the default backend and preserves the existing behavior.
    """

    def __init__(self, base_path: str):
        self.base_path = os.path.abspath(base_path)
        os.makedirs(self.base_path, exist_ok=True)

    def _full_path(self, key: str) -> str:
        return os.path.join(self.base_path, key.replace("/", os.sep))

    async def write(self, key: str, data: bytes) -> None:
        path = self._full_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)

    async def read(self, key: str) -> bytes:
        path = self._full_path(key)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Blob not found: {key}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> bool:
        path = self._full_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return os.path.exists(self._full_path(key))

    async def delete_prefix(self, prefix: str) -> int:
        path = self._full_path(prefix)
        if os.path.exists(path) and os.path.isdir(path):
            count = sum(len(files) for _, _, files in os.walk(path))
            shutil.rmtree(path)
            return count
        return 0

    def get_storage_stats(self) -> dict:
        total_size = 0
        total_files = 0
        for dirpath, _, filenames in os.walk(self.base_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
                total_files += 1
        return {
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "total_files": total_files,
            "storage_path": self.base_path,
            "backend": "local",
        }


# ═══════════════════════════════════════════════════════════════════════════
#  Azure Blob Storage Backend
# ═══════════════════════════════════════════════════════════════════════════

class AzureBlobStorageBackend(StorageBackend):
    """Azure Blob Storage backend for production deployments.

    Uses the azure-storage-blob async SDK. Each key maps to a blob name
    within the configured container.
    """

    def __init__(self, connection_string: str, container_name: str):
        try:
            from azure.storage.blob.aio import BlobServiceClient
        except ImportError:
            raise ImportError(
                "azure-storage-blob is required for Azure backend. "
                "Install with: pip install azure-storage-blob"
            )
        self.connection_string = connection_string
        self.container_name = container_name
        self._client = BlobServiceClient.from_connection_string(connection_string)
        self._container = self._client.get_container_client(container_name)

    async def _ensure_container(self):
        """Create container if it doesn't exist."""
        try:
            await self._container.create_container()
        except Exception:
            pass  # Container already exists

    async def write(self, key: str, data: bytes) -> None:
        await self._ensure_container()
        blob = self._container.get_blob_client(key)
        await blob.upload_blob(data, overwrite=True)

    async def read(self, key: str) -> bytes:
        blob = self._container.get_blob_client(key)
        try:
            stream = await blob.download_blob()
            return await stream.readall()
        except Exception as e:
            raise FileNotFoundError(f"Blob not found: {key}") from e

    async def delete(self, key: str) -> bool:
        blob = self._container.get_blob_client(key)
        try:
            await blob.delete_blob()
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        blob = self._container.get_blob_client(key)
        try:
            await blob.get_blob_properties()
            return True
        except Exception:
            return False

    async def delete_prefix(self, prefix: str) -> int:
        count = 0
        async for blob in self._container.list_blobs(name_starts_with=prefix):
            await self._container.delete_blob(blob.name)
            count += 1
        return count

    def get_storage_stats(self) -> dict:
        # Note: Full stats require listing all blobs — expensive for large containers.
        # For production, use Azure Monitor metrics instead.
        return {
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "total_files": 0,
            "storage_path": f"azure://{self.container_name}",
            "backend": "azure",
        }


# ═══════════════════════════════════════════════════════════════════════════
#  MinIO / S3-Compatible Backend
# ═══════════════════════════════════════════════════════════════════════════

class MinIOStorageBackend(StorageBackend):
    """S3-compatible storage backend for MinIO (Docker dev) and AWS S3.

    Uses aioboto3 for async S3 operations. Keys map directly to S3 object keys.
    """

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        use_ssl: bool = False,
        region: str = "us-east-1",
    ):
        try:
            import aioboto3
        except ImportError:
            raise ImportError(
                "aioboto3 is required for MinIO/S3 backend. "
                "Install with: pip install aioboto3"
            )
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.use_ssl = use_ssl
        self.region = region
        self._session = aioboto3.Session()

    def _endpoint_url(self) -> str:
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.endpoint}"

    def _client_kwargs(self) -> dict:
        return {
            "service_name": "s3",
            "endpoint_url": self._endpoint_url(),
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "region_name": self.region,
        }

    async def _ensure_bucket(self):
        """Create bucket if it doesn't exist."""
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                await s3.head_bucket(Bucket=self.bucket)
            except Exception:
                try:
                    await s3.create_bucket(Bucket=self.bucket)
                except Exception:
                    pass  # Bucket may already exist

    async def write(self, key: str, data: bytes) -> None:
        async with self._session.client(**self._client_kwargs()) as s3:
            await s3.put_object(Bucket=self.bucket, Key=key, Body=data)

    async def read(self, key: str) -> bytes:
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                response = await s3.get_object(Bucket=self.bucket, Key=key)
                return await response["Body"].read()
            except Exception as e:
                raise FileNotFoundError(f"Blob not found: {key}") from e

    async def delete(self, key: str) -> bool:
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                await s3.delete_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def exists(self, key: str) -> bool:
        async with self._session.client(**self._client_kwargs()) as s3:
            try:
                await s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def delete_prefix(self, prefix: str) -> int:
        count = 0
        async with self._session.client(**self._client_kwargs()) as s3:
            paginator = s3.get_paginator("list_objects_v2")
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                objects = page.get("Contents", [])
                if objects:
                    delete_req = {"Objects": [{"Key": obj["Key"]} for obj in objects]}
                    await s3.delete_objects(Bucket=self.bucket, Delete=delete_req)
                    count += len(objects)
        return count

    def get_storage_stats(self) -> dict:
        return {
            "total_size_bytes": 0,
            "total_size_mb": 0,
            "total_files": 0,
            "storage_path": f"s3://{self.bucket}",
            "backend": "minio",
        }
