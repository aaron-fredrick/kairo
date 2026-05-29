"""
Storage backend abstraction (legacy upload URLs / thumbnail worker).

For content-addressed blobs, see app_backend.storage.provider and blob_manager.
"""
from __future__ import annotations

import asyncio
import ftplib
import io
from abc import ABC, abstractmethod

import aiofiles
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app_backend.core.config import settings
from app_backend.core.logging import get_logger

logger = get_logger(__name__)


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, data: bytes, relative_path: str) -> str:
        """Persist *data* and return the public URL for the stored object."""


class LocalStorage(StorageBackend):
    """Saves files under DATA_DIR and serves them via the API."""

    async def save(self, data: bytes, relative_path: str) -> str:
        import os

        abs_path = os.path.join(settings.DATA_DIR, relative_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        async with aiofiles.open(abs_path, "wb") as f:
            await f.write(data)

        logger.debug("LocalStorage: wrote %d bytes to '%s'", len(data), abs_path)
        return f"{settings.API_BASE_URL.rstrip('/api')}/{relative_path}"


class S3Storage(StorageBackend):
    """Uploads files to an S3-compatible object store (AWS S3, MinIO, etc.)."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint_url: str | None = None,
    ) -> None:
        client_kwargs: dict = {
            "region_name": region,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
            client_kwargs["config"] = Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
        self._bucket = bucket
        self._region = region
        self._endpoint_url = endpoint_url
        self._client = boto3.client("s3", **client_kwargs)

    async def save(self, data: bytes, relative_path: str) -> str:
        loop = asyncio.get_event_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object(
                    Bucket=self._bucket,
                    Key=relative_path,
                    Body=data,
                ),
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error("S3Storage upload failed for '%s': %s", relative_path, exc)
            raise

        logger.debug("S3Storage: uploaded '%s' to bucket '%s'", relative_path, self._bucket)

        if self._endpoint_url:
            base = self._endpoint_url.rstrip("/")
            return f"{base}/{self._bucket}/{relative_path}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{relative_path}"


class FTPStorage(StorageBackend):
    """Uploads files to an FTP server using a thread-pool executor."""

    def _blocking_upload(self, data: bytes, remote_path: str) -> None:
        with ftplib.FTP() as ftp:
            ftp.connect(settings.FTP_HOST, settings.FTP_PORT)
            ftp.login(settings.FTP_USER, settings.FTP_PASSWORD)
            parts = remote_path.replace("\\", "/").split("/")
            for i in range(1, len(parts)):
                directory = "/".join(parts[:i])
                if directory:
                    try:
                        ftp.mkd(directory)
                    except ftplib.error_perm:
                        pass
            ftp.storbinary(f"STOR {remote_path}", io.BytesIO(data))

    async def save(self, data: bytes, relative_path: str) -> str:
        remote_path = f"{settings.FTP_REMOTE_DIR}/{relative_path}"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._blocking_upload, data, remote_path)
        logger.debug(
            "FTPStorage: uploaded '%s' to '%s:%d'",
            relative_path,
            settings.FTP_HOST,
            settings.FTP_PORT,
        )
        return f"{settings.API_BASE_URL}/{relative_path}"


def get_storage_backend() -> StorageBackend:
    """Factory: return the configured legacy storage backend."""
    backend = settings.UPLOAD_BACKEND.lower()
    if backend == "s3":
        cfg = settings.object_storage_config("s3")
        return S3Storage(
            bucket=cfg["bucket"],
            region=cfg["region"],
            access_key=cfg["access_key"],
            secret_key=cfg["secret_key"],
            endpoint_url=cfg["endpoint_url"] or None,
        )
    if backend == "minio":
        cfg = settings.object_storage_config("minio")
        return S3Storage(
            bucket=cfg["bucket"],
            region=cfg["region"],
            access_key=cfg["access_key"],
            secret_key=cfg["secret_key"],
            endpoint_url=cfg["endpoint_url"] or None,
        )
    if backend == "ftp":
        return FTPStorage()
    return LocalStorage()


storage_backend: StorageBackend = get_storage_backend()
