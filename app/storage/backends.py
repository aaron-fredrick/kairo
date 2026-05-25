"""
Storage backend abstraction.

Each backend exposes a single coroutine:
    save(data: bytes, relative_path: str) -> str
        Persists raw bytes and returns the canonical public URL.
"""
from __future__ import annotations

import asyncio
import ftplib
import io
from abc import ABC, abstractmethod

import aiofiles
import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, relative_path: str) -> str:
        """Persist *data* and return the public URL for the stored object."""


class LocalStorage(StorageBackend):
    """Saves files to a local directory and serves them via FastAPI StaticFiles."""

    async def save(self, data: bytes, relative_path: str) -> str:
        import os
        abs_path = os.path.join(settings.UPLOAD_LOCAL_DIR, relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(data)

        logger.debug("LocalStorage: wrote %d bytes to '%s'", len(data), abs_path)
        return f"{settings.UPLOAD_BASE_URL}/{relative_path}"


class S3Storage(StorageBackend):
    """Uploads files to an S3-compatible object store (AWS S3, MinIO, etc.)."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT_URL or None,
        )

    async def save(self, data: bytes, relative_path: str) -> str:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    Bucket=settings.S3_BUCKET,
                    Key=relative_path,
                    Body=data,
                ),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3Storage upload failed for '%s': %s", relative_path, exc)
            raise

        logger.debug("S3Storage: uploaded '%s' to bucket '%s'", relative_path, settings.S3_BUCKET)

        if settings.S3_ENDPOINT_URL:
            return f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET}/{relative_path}"
        return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{relative_path}"


class FTPStorage(StorageBackend):
    """Uploads files to an FTP server using a thread-pool executor."""

    def _blocking_upload(self, data: bytes, remote_path: str) -> None:
        with ftplib.FTP() as ftp:
            ftp.connect(settings.FTP_HOST, settings.FTP_PORT)
            ftp.login(settings.FTP_USER, settings.FTP_PASSWORD)
            # Ensure remote directory exists
            parts = remote_path.replace("\\", "/").split("/")
            for i in range(1, len(parts)):
                directory = "/".join(parts[:i])
                if directory:
                    try:
                        ftp.mkd(directory)
                    except ftplib.error_perm:
                        pass  # Directory likely already exists
            ftp.storbinary(f"STOR {remote_path}", io.BytesIO(data))

    async def save(self, data: bytes, relative_path: str) -> str:
        remote_path = f"{settings.FTP_REMOTE_DIR}/{relative_path}"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._blocking_upload, data, remote_path)
        logger.debug("FTPStorage: uploaded '%s' to '%s:%d'", relative_path, settings.FTP_HOST, settings.FTP_PORT)
        return f"{settings.UPLOAD_BASE_URL}/{relative_path}"


def get_storage_backend() -> StorageBackend:
    """Factory: return the configured storage backend singleton."""
    backend = settings.UPLOAD_BACKEND.lower()
    if backend == "s3":
        return S3Storage()
    if backend == "ftp":
        return FTPStorage()
    return LocalStorage()


# Module-level singleton — one instance for the lifetime of the process.
storage_backend: StorageBackend = get_storage_backend()
