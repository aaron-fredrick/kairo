"""
Storage provider interface and implementations.

This module defines the StorageProvider protocol (put/get/exists/delete)
and concrete implementations. All blobs are keyed by their content-addressed
SHA-256 hash and stored with two-level directory sharding:

    blobs/sha256/<first-2-hex>/<next-2-hex>/<full-hash>

This structure limits directory fan-out for filesystems that degrade
on directories with millions of direct children.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod

import aiofiles

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
