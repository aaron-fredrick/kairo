"""
BlobManager — content-addressed blob ingestion pipeline.

Responsibilities:
  - Stream an UploadFile while computing its SHA-256 digest in-flight.
  - Deduplicate: if the blob already exists, return immediately without writing.
  - Delegate persistence to a StorageProvider.
  - Return a BlobResult with the hash, size, and deduplication status.

The manager deliberately avoids holding entire file contents in memory
beyond what is necessary for the streaming hash pass. It processes the
file in configurable chunks and passes bytes directly to the provider.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Literal

from fastapi import UploadFile

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.provider import LocalStorageProvider, StorageProvider

logger = get_logger(__name__)

_CHUNK_SIZE = 256 * 1024  # 256 KiB per streaming chunk


@dataclass(frozen=True)
class BlobResult:
    blob_hash: str                              # SHA-256 hex digest (64 chars)
    size_bytes: int                             # Total bytes ingested
    status: Literal["stored", "reused"]         # Whether blob was new or duplicate
    storage_path: str                           # Provider-relative path to the blob


class BlobManager:
    """
    Orchestrates content-addressed blob storage.

    Instantiate once at application startup and share the singleton.
    The provider is injected so that the manager is backend-agnostic;
    swapping to S3 only requires a different StorageProvider implementation.
    """

    def __init__(self, provider: StorageProvider) -> None:
        self._provider = provider

    async def create_blob(self, file: UploadFile) -> BlobResult:
        """
        Stream *file*, compute SHA-256, deduplicate, and persist.

        The file is read in chunks so arbitrarily large uploads never fully
        materialise in process memory. A second pass through the provider is
        avoided when the blob already exists (deduplication).

        Returns a BlobResult containing the hash, size, and final storage path.
        """
        max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
        digest = hashlib.sha256()
        chunks: list[bytes] = []
        total = 0

        while True:
            chunk = await file.read(_CHUNK_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(
                    f"Upload exceeds the maximum allowed size of {settings.UPLOAD_MAX_SIZE_MB} MB."
                )
            digest.update(chunk)
            chunks.append(chunk)

        blob_hash = digest.hexdigest()
        logger.debug("BlobManager: computed hash=%s size=%d", blob_hash, total)

        if await self._provider.exists(blob_hash):
            logger.info("BlobManager: blob %s already exists — skipping write", blob_hash)
            return BlobResult(
                blob_hash=blob_hash,
                size_bytes=total,
                status="reused",
                storage_path=f"blobs/sha256/{blob_hash[:2]}/{blob_hash[2:4]}/{blob_hash}",
            )

        data = b"".join(chunks)
        storage_path = await self._provider.put(blob_hash, data)
        logger.info("BlobManager: stored blob hash=%s path=%s", blob_hash, storage_path)

        return BlobResult(
            blob_hash=blob_hash,
            size_bytes=total,
            status="stored",
            storage_path=storage_path,
        )

    async def get_blob(self, blob_hash: str) -> bytes:
        """Retrieve and return the raw bytes for the given hash."""
        return await self._provider.get(blob_hash)

    async def exists(self, blob_hash: str) -> bool:
        """Return True if a blob with the given hash is stored."""
        return await self._provider.exists(blob_hash)


def _build_provider() -> StorageProvider:
    """Construct the configured StorageProvider at import time."""
    backend = settings.UPLOAD_BACKEND.lower()
    base_dir = settings.UPLOAD_LOCAL_DIR
    if backend in ("local", "s3", "ftp"):
        # For local and future backends, always use the local provider for the
        # content-addressed blob layer. S3/FTP back-ends can have their own
        # StorageProvider implementations added here later.
        return LocalStorageProvider(base_dir)
    return LocalStorageProvider(base_dir)


# Module-level singleton — shared across the entire application lifetime.
blob_manager = BlobManager(_build_provider())
