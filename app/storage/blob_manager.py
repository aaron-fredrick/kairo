"""
BlobManager — content-addressed blob ingestion pipeline.
"""
from __future__ import annotations

import io
import hashlib
from dataclasses import dataclass
from typing import Literal

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.provider import StorageProvider, get_storage_provider

logger = get_logger(__name__)


@dataclass(frozen=True)
class BlobResult:
    blob_hash: str
    size_bytes: int
    status: Literal["stored", "reused"]
    storage_path: str


class BlobManager:
    def __init__(self, provider: StorageProvider) -> None:
        self._provider = provider

    async def create_blob_from_bytes(self, data: bytes, mime_type: str = "") -> BlobResult:
        max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
        if len(data) > max_bytes:
            raise ValueError(
                f"Upload exceeds the maximum allowed size of {settings.UPLOAD_MAX_SIZE_MB} MB."
            )

        if mime_type.startswith("image/"):
            try:
                img = Image.open(io.BytesIO(data))
                fmt = img.format or "PNG"
                buf = io.BytesIO()
                if fmt == "JPEG":
                    img.save(buf, format="JPEG", quality=95)
                elif fmt in ("PNG", "WEBP", "GIF"):
                    img.save(buf, format=fmt)
                else:
                    img.save(buf, format="PNG")
                data = buf.getvalue()
                logger.debug("Stripped EXIF from image, new size: %d", len(data))
            except UnidentifiedImageError:
                logger.warning("Failed to parse image for EXIF stripping, storing as-is")

        blob_hash = hashlib.sha256(data).hexdigest()
        total = len(data)
        logger.debug("BlobManager: computed hash=%s size=%d", blob_hash, total)

        storage_path = f"blobs/sha256/{blob_hash[:2]}/{blob_hash[2:4]}/{blob_hash}"
        if await self._provider.exists(blob_hash):
            logger.info("BlobManager: blob %s already exists — skipping write", blob_hash)
            return BlobResult(
                blob_hash=blob_hash,
                size_bytes=total,
                status="reused",
                storage_path=storage_path,
            )

        storage_path = await self._provider.put(blob_hash, data)
        logger.info("BlobManager: stored blob hash=%s path=%s", blob_hash, storage_path)

        return BlobResult(
            blob_hash=blob_hash,
            size_bytes=total,
            status="stored",
            storage_path=storage_path,
        )

    async def create_blob_from_path(self, file_path: str, mime_type: str = "") -> BlobResult:
        """Read a local file path (legacy); prefer create_blob_from_bytes + storage provider."""
        import aiofiles

        async with aiofiles.open(file_path, "rb") as fh:
            data = await fh.read()
        return await self.create_blob_from_bytes(data, mime_type=mime_type)

    async def get_blob(self, blob_hash: str) -> bytes:
        return await self._provider.get(blob_hash)

    async def exists(self, blob_hash: str) -> bool:
        return await self._provider.exists(blob_hash)


blob_manager = BlobManager(get_storage_provider())
