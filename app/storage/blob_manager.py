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

import io
import os
import hashlib
from dataclasses import dataclass
from typing import Literal

import aiofiles
from PIL import Image, UnidentifiedImageError

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

    async def create_blob_from_path(self, file_path: str, mime_type: str = "") -> BlobResult:
        """
        Read from *file_path*, strip EXIF if it's an image, compute SHA-256,
        deduplicate, and persist.

        Returns a BlobResult containing the hash, size, and final storage path.
        """
        max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
        file_size = os.path.getsize(file_path)
        
        if file_size > max_bytes:
            raise ValueError(f"Upload exceeds the maximum allowed size of {settings.UPLOAD_MAX_SIZE_MB} MB.")

        # Read the file into memory
        async with aiofiles.open(file_path, "rb") as fh:
            data = await fh.read()

        # Strip EXIF for images
        if mime_type.startswith("image/"):
            try:
                # Open with Pillow, which ignores EXIF by default unless requested.
                # Re-saving strips it.
                img = Image.open(io.BytesIO(data))
                
                # We need to preserve the format if possible, otherwise fallback to PNG (lossless)
                fmt = img.format or "PNG"
                if fmt == "JPEG":
                    # For JPEGs, save with high quality to minimize re-compression loss
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=95)
                    data = buf.getvalue()
                elif fmt in ("PNG", "WEBP", "GIF"):
                    # Lossless formats
                    buf = io.BytesIO()
                    img.save(buf, format=fmt)
                    data = buf.getvalue()
                else:
                    # Fallback
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    data = buf.getvalue()
                    
                logger.debug("Stripped EXIF from image, new size: %d", len(data))
            except UnidentifiedImageError:
                logger.warning("Failed to parse image for EXIF stripping, storing as-is")

        # Now hash the (possibly cleaned) data
        blob_hash = hashlib.sha256(data).hexdigest()
        total = len(data)
        logger.debug("BlobManager: computed hash=%s size=%d", blob_hash, total)

        if await self._provider.exists(blob_hash):
            logger.info("BlobManager: blob %s already exists — skipping write", blob_hash)
            return BlobResult(
                blob_hash=blob_hash,
                size_bytes=total,
                status="reused",
                storage_path=f"blobs/sha256/{blob_hash[:2]}/{blob_hash[2:4]}/{blob_hash}",
            )

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
    base_dir = settings.DATA_DIR
    if backend in ("local", "s3", "ftp"):
        return LocalStorageProvider(base_dir)
    return LocalStorageProvider(base_dir)


# Module-level singleton — shared across the entire application lifetime.
blob_manager = BlobManager(_build_provider())
