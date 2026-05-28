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
from app.services.thumbnail_service import THUMBNAIL_SIZES, generate_and_save_thumbnails
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
    room_id: int = 0



# ---- Global queue ----------------------------------------------------------

thumbnail_queue: asyncio.Queue[ThumbnailJob] = asyncio.Queue()


# ---- Worker coroutine ------------------------------------------------------

async def _process_job(job: ThumbnailJob, storage: StorageBackend) -> None:
    from sqlalchemy import select

    from app.db.database import AsyncSessionLocal
    from app.db.redis import redis_manager
    from app.models.upload import Upload

    logger.info("Thumbnail worker: processing hash_id='%s'", job.hash_id)

    # The service now handles saving the thumbnails and returns a map of label -> URL
    thumbnail_urls = await generate_and_save_thumbnails(
        blob_hash=job.hash_id,
        data=job.file_data,
        mime_type=job.mime_type,
        extension=job.extension,
    )

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Upload).where(Upload.hash_id == job.hash_id))
        upload: Upload | None = result.scalars().first()

        if upload is None:
            logger.error("Thumbnail worker: no Upload record found for hash_id='%s'", job.hash_id)
            return

        upload.thumbnails_ready = True
        # thumbnail_sha256 fields are no longer strictly tracked in DB for now,
        # or we could extract them if we wanted, but the DB schema only has sm/md/lg.
        await db.commit()

    from app.workers.broadcast import BroadcastJob, broadcast_queue

    await broadcast_queue.put(
        BroadcastJob(
            room_id=job.room_id,
            event_type="thumbnails_ready",
            payload={
                "hash_id": job.hash_id,
                "thumbnails": thumbnail_urls,
            },
        )
    )
    logger.info("Thumbnail worker: completed hash_id='%s' — broadcast queued", job.hash_id)



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
