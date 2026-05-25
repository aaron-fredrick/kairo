"""
Async thumbnail worker.

A single asyncio.Queue is used as the task bus.  On startup the worker
coroutine is spawned as a background task and drains jobs indefinitely.

Each job carries everything the worker needs:
    - The raw file bytes (already saved to the primary store)
    - The Upload.hash_id for path derivation and DB lookup
    - mime_type and extension for thumbnail logic
    - A reference to the storage backend and DB session factory
    - A reference to the optional Redis client
"""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.services.thumbnail_service import THUMBNAIL_SIZES, generate_thumbnails
from app.storage.backends import StorageBackend

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# ---- Job definition --------------------------------------------------------

@dataclass
class ThumbnailJob:
    hash_id: str
    file_data: bytes
    mime_type: str
    extension: str


# ---- Global queue ----------------------------------------------------------

thumbnail_queue: asyncio.Queue[ThumbnailJob] = asyncio.Queue()


# ---- Worker coroutine ------------------------------------------------------

async def _process_job(job: ThumbnailJob, storage: StorageBackend) -> None:
    from sqlalchemy import select

    from app.db.database import AsyncSessionLocal
    from app.db.redis import redis_manager
    from app.models.upload import Upload

    logger.info("Thumbnail worker: processing hash_id='%s'", job.hash_id)

    thumbnails = await generate_thumbnails(job.file_data, job.mime_type, job.extension)

    sha256s: dict[str, str] = {}
    for label, (thumb_bytes, digest) in thumbnails.items():
        w, h = THUMBNAIL_SIZES[label]
        relative_path = f"thumbnails/{job.hash_id}_{w}x{h}.jpeg"
        await storage.save(thumb_bytes, relative_path)
        sha256s[label] = digest
        logger.debug(
            "Thumbnail worker: saved %s thumbnail for '%s' (%d bytes)",
            label, job.hash_id, len(thumb_bytes),
        )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Upload).where(Upload.hash_id == job.hash_id))
        upload: Upload | None = result.scalars().first()

        if upload is None:
            logger.error("Thumbnail worker: no Upload record found for hash_id='%s'", job.hash_id)
            return

        upload.thumbnails_ready = True
        upload.thumbnail_sha256_sm = sha256s.get("sm")
        upload.thumbnail_sha256_md = sha256s.get("md")
        upload.thumbnail_sha256_lg = sha256s.get("lg")
        await db.commit()

    # Notify Redis (if available) so connected WebSocket clients can refresh
    redis = redis_manager.get_client()
    try:
        from app.db.redis import MockRedis
        if not isinstance(redis, MockRedis):
            await redis.publish(
                f"thumbnails:{job.hash_id}",
                "ready",
            )
    except Exception as exc:
        logger.warning("Thumbnail worker: Redis publish failed: %s", exc)

    logger.info("Thumbnail worker: completed hash_id='%s'", job.hash_id)


async def run_thumbnail_worker(storage: StorageBackend) -> None:
    """Long-running coroutine; drain the queue forever."""
    logger.info("Thumbnail worker started")
    while True:
        job: ThumbnailJob = await thumbnail_queue.get()
        try:
            await _process_job(job, storage)
        except Exception as exc:
            logger.error(
                "Thumbnail worker: unhandled error for hash_id='%s': %s",
                job.hash_id, exc, exc_info=True,
            )
        finally:
            thumbnail_queue.task_done()
