"""
Storage provider interface and implementations.

Backends are selected via UPLOAD_BACKEND (local | s3 | minio | ftp).
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

logger = get_logger(__name__)


class StorageProvider(ABC):
    """
    Content-addressed blob storage interface.

    All keys are expected to be SHA-256 hex digests (64 characters).
    """

    @abstractmethod
    async def put(self, key: str, data: bytes) -> str:
        """
        Persist *data* under *key*.

        Returns the provider-relative path to the stored blob.
        Implementations MUST be idempotent — writing the same key twice
        is safe and does not corrupt existing data.
        """

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Return the raw bytes for *key*. Raises FileNotFoundError if absent."""

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Return True if a blob with *key* is already stored."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Remove the blob for *key*. No-ops silently if the key is absent."""


def _shard_path(key: str) -> str:
    """
    Derive a two-level sharded relative path from a SHA-256 hex digest.

    Example:
        key  = "8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
        path = "blobs/sha256/8f/43/8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4"
    """
    return os.path.join("blobs", "sha256", key[:2], key[2:4], key)


class LocalStorageProvider(StorageProvider):
    """
    Filesystem blob store with SHA-256 content addressing and path sharding.

    All blobs live under *base_dir*; the directory is created on first use.
    """

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir

    def _abs(self, key: str) -> str:
        return os.path.join(self._base_dir, _shard_path(key))

    async def put(self, key: str, data: bytes) -> str:
        abs_path = self._abs(key)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        async with aiofiles.open(abs_path, "wb") as fh:
            await fh.write(data)
        logger.debug("LocalStorageProvider.put: wrote %d bytes → %s", len(data), abs_path)
        return _shard_path(key)

    async def get(self, key: str) -> bytes:
        abs_path = self._abs(key)
        if not os.path.exists(abs_path):
            raise FileNotFoundError(f"Blob not found: {key}")
        async with aiofiles.open(abs_path, "rb") as fh:
            return await fh.read()

    async def exists(self, key: str) -> bool:
        return os.path.exists(self._abs(key))

    async def delete(self, key: str) -> None:
        abs_path = self._abs(key)
        if os.path.exists(abs_path):
            os.remove(abs_path)
            logger.debug("LocalStorageProvider.delete: removed %s", abs_path)


class S3StorageProvider(StorageProvider):
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

    def _object_key(self, key: str) -> str:
        return _shard_path(key)

    async def put(self, key: str, data: bytes) -> str:
        object_key = self._object_key(key)
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
            logger.error("S3StorageProvider.put failed for '%s': %s", object_key, exc)
            raise
        logger.debug(
            "S3StorageProvider.put: %d bytes → s3://%s/%s",
            len(data),
            self._bucket,
            object_key,
        )
        return object_key

    async def get(self, key: str) -> bytes:
        object_key = self._object_key(key)
        loop = asyncio.get_event_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: self._client.get_object(Bucket=self._bucket, Key=object_key),
            )
            return response["Body"].read()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                raise FileNotFoundError(f"Blob not found: {key}") from exc
            raise

    async def exists(self, key: str) -> bool:
        object_key = self._object_key(key)
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

    async def delete(self, key: str) -> None:
        object_key = self._object_key(key)
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


def build_storage_provider(backend: str | None = None) -> StorageProvider:
    """Factory for content-addressed blob StorageProvider implementations."""
    name = (backend or settings.UPLOAD_BACKEND).lower()
    if name == "local":
        return LocalStorageProvider(settings.DATA_DIR)
    if name in ("s3", "minio"):
        cfg = settings.object_storage_config(name)
        return S3StorageProvider(
            bucket=cfg["bucket"],
            region=cfg["region"],
            access_key=cfg["access_key"],
            secret_key=cfg["secret_key"],
            endpoint_url=cfg["endpoint_url"] or None,
        )
    if name == "ftp":
        logger.warning(
            "UPLOAD_BACKEND=ftp uses legacy FTP upload paths; blobs stay on local disk"
        )
        return LocalStorageProvider(settings.DATA_DIR)
    logger.warning("Unknown UPLOAD_BACKEND '%s', falling back to local", name)
    return LocalStorageProvider(settings.DATA_DIR)
