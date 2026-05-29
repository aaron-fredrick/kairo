"""
Storage provider interface and implementations.

Backends are selected via UPLOAD_BACKEND (local | s3 | minio | ftp).
All artifacts (blobs, temp uploads, thumbnails, pfps) share one provider.
"""
from __future__ import annotations

import asyncio
import os
from abc import ABC, abstractmethod

import aiofiles
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.paths import normalize_posix_path

logger = get_logger(__name__)


class StorageProvider(ABC):
    """Unified object storage for blobs and other artifacts."""

    @abstractmethod
    async def put_path(self, rel_path: str, data: bytes) -> str:
        """Persist *data* at *rel_path* (POSIX). Returns the stored path."""

    @abstractmethod
    async def get_path(self, rel_path: str) -> bytes:
        """Return bytes at *rel_path*. Raises FileNotFoundError if absent."""

    @abstractmethod
    async def exists_path(self, rel_path: str) -> bool:
        """Return True if *rel_path* exists."""

    @abstractmethod
    async def delete_path(self, rel_path: str) -> None:
        """Remove *rel_path*. No-ops if absent."""

    async def put(self, key: str, data: bytes) -> str:
        """Content-addressed blob write (SHA-256 hex *key*)."""
        return await self.put_path(_blob_shard_path(key), data)

    async def get(self, key: str) -> bytes:
        return await self.get_path(_blob_shard_path(key))

    async def exists(self, key: str) -> bool:
        return await self.exists_path(_blob_shard_path(key))

    async def delete(self, key: str) -> None:
        await self.delete_path(_blob_shard_path(key))


def _blob_shard_path(key: str) -> str:
    """POSIX object key for a content-addressed blob."""
    return f"blobs/sha256/{key[:2]}/{key[2:4]}/{key}"


def _local_shard_path(key: str) -> str:
    """Filesystem-relative path under DATA_DIR (local backend only)."""
    return os.path.join("blobs", "sha256", key[:2], key[2:4], key)


class LocalStorageProvider(StorageProvider):
    """Filesystem store under *base_dir*."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir

    def _abs_path(self, rel_path: str) -> str:
        parts = normalize_posix_path(rel_path).split("/")
        return os.path.join(self._base_dir, *parts)

    async def put_path(self, rel_path: str, data: bytes) -> str:
        rel = normalize_posix_path(rel_path)
        abs_path = self._abs_path(rel)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        async with aiofiles.open(abs_path, "wb") as fh:
            await fh.write(data)
        logger.debug("LocalStorageProvider.put_path: wrote %d bytes → %s", len(data), abs_path)
        return rel

    async def get_path(self, rel_path: str) -> bytes:
        abs_path = self._abs_path(rel_path)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Object not found: {rel_path}")
        async with aiofiles.open(abs_path, "rb") as fh:
            return await fh.read()

    async def exists_path(self, rel_path: str) -> bool:
        return os.path.exists(self._abs_path(rel_path))

    async def delete_path(self, rel_path: str) -> None:
        abs_path = self._abs_path(rel_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            logger.debug("LocalStorageProvider.delete_path: removed %s", abs_path)


class S3StorageProvider(StorageProvider):  # pragma: no cover
    """S3-compatible object store (AWS S3 or custom endpoint)."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str | None = None,
        use_path_style: bool | None = None,
    ) -> None:
        if not bucket:
            raise ValueError("Object storage bucket name is required")
        self._bucket = bucket
        path_style = use_path_style if use_path_style is not None else bool(endpoint_url)
        client_kwargs: dict = {
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if path_style:
            client_kwargs["config"] = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
        self._client = boto3.client("s3", **client_kwargs)
        self._region = region
        self.ensure_bucket_exists()

    def ensure_bucket_exists(self) -> None:
        """Create the bucket if missing (needed for local MinIO without mc init)."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
            logger.debug("Object storage bucket '%s' exists", self._bucket)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code not in ("404", "NoSuchBucket", "NotFound"):
                raise
            kwargs: dict = {"Bucket": self._bucket}
            if self._region and self._region != "us-east-1":
                kwargs["CreateBucketConfiguration"] = {"LocationConstraint": self._region}
            self._client.create_bucket(**kwargs)
            logger.info("Created object storage bucket '%s'", self._bucket)

    def _object_key(self, rel_path: str) -> str:
        return normalize_posix_path(rel_path)

    async def put_path(self, rel_path: str, data: bytes) -> str:
        object_key = self._object_key(rel_path)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Key=object_key,
                    Body=data,
                ),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3StorageProvider.put_path failed for '%s': %s", object_key, exc)
            raise
        logger.debug(
            "S3StorageProvider.put_path: %d bytes → s3://%s/%s",
            len(data),
            self._bucket,
            object_key,
        )
        return object_key

    async def get_path(self, rel_path: str) -> bytes:
        object_key = self._object_key(rel_path)
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.get_object(Bucket=self._bucket, Key=object_key),
            )
            return response["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                raise FileNotFoundError(f"Object not found: {rel_path}") from exc
            raise

    async def exists_path(self, rel_path: str) -> bool:
        object_key = self._object_key(rel_path)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.head_object(Bucket=self._bucket, Key=object_key),
            )
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    async def delete_path(self, rel_path: str) -> None:
        object_key = self._object_key(rel_path)
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.delete_object(Bucket=self._bucket, Key=object_key),
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in ("404", "NoSuchKey", "NotFound"):
                return
            raise


_provider: StorageProvider | None = None


def build_storage_provider(backend: str | None = None) -> StorageProvider:
    """Factory for StorageProvider implementations."""
    name = (backend or settings.UPLOAD_BACKEND).lower()
    if name == "local":
        return LocalStorageProvider(settings.DATA_DIR)
    if name in ("s3", "minio"):  # pragma: no cover
        cfg = settings.object_storage_config(name)
        return S3StorageProvider(
            bucket=cfg["bucket"],
            region=cfg["region"],
            access_key=cfg["access_key"],
            secret_key=cfg["secret_key"],
            endpoint_url=cfg["endpoint_url"] or None,
        )
    if name == "ftp":  # pragma: no cover
        logger.warning(
            "UPLOAD_BACKEND=ftp uses legacy FTP upload paths; artifacts stay on local disk"
        )
        return LocalStorageProvider(settings.DATA_DIR)
    logger.warning("Unknown UPLOAD_BACKEND '%s', falling back to local", name)
    return LocalStorageProvider(settings.DATA_DIR)


def get_storage_provider() -> StorageProvider:
    """Application-wide storage provider singleton."""
    global _provider
    if _provider is None:
        _provider = build_storage_provider()
        logger.info("Storage backend: %s", settings.UPLOAD_BACKEND.lower())
    return _provider
