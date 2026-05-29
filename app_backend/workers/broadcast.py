"""
Broadcast worker.

A dedicated asyncio.Queue drains BroadcastJob items and fans the JSON event
out to the abstract EventBus.

The EventBus handles delivering the message to the appropriate WebSocket clients,
either locally (LocalEventBus) or across horizontal nodes (RedisEventBus).

Event types:
  file_uploaded   — emitted immediately when a file is saved (thumbnails may not be ready)
  thumbnails_ready — emitted by the thumbnail worker once all three sizes are persisted
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict

from app_backend.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Job definition
# ---------------------------------------------------------------------------

@dataclass
class BroadcastJob:
    """A single event to be broadcast to a room's connected WebSocket clients."""
    room_id: int
    event_type: str           # e.g. "file_uploaded" | "thumbnails_ready"
    payload: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Global queue
# ---------------------------------------------------------------------------

broadcast_queue: asyncio.Queue[BroadcastJob] = asyncio.Queue()


# ---------------------------------------------------------------------------
# Worker coroutine
# ---------------------------------------------------------------------------

async def _process_broadcast(job: BroadcastJob) -> None:
    from app_backend.core.event_bus import event_bus

    envelope = json.dumps({
        "event": job.event_type,
        **job.payload,
    })

    channel = f"room:{job.room_id}:events"
    try:
        await event_bus.publish(channel, envelope)
    except Exception as exc:
        logger.warning("EventBus publish failed for channel '%s': %s", channel, exc)


async def run_broadcast_worker() -> None:
    """Long-running coroutine; drain the broadcast queue forever."""
    logger.info("Broadcast worker started")
    while True:
        job: BroadcastJob = await broadcast_queue.get()
        try:
            await _process_broadcast(job)
        except Exception as exc:
            logger.error(
                "Broadcast worker: unhandled error for event '%s' room_id=%d: %s",
                job.event_type, job.room_id, exc, exc_info=True,
            )
        finally:
            broadcast_queue.task_done()
