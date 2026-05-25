"""
Broadcast worker.

A dedicated asyncio.Queue drains BroadcastJob items and fans the JSON event
out to every WebSocket client in the target room via the local ConnectionManager.

When Redis pub/sub is active (USE_REDIS=True) the event is also published to
  channel "room:{room_id}:events"
so that peer server nodes (horizontal scale) can relay it to their own sockets.

Event types:
  file_uploaded   — emitted immediately when a file is saved (thumbnails may not be ready)
  thumbnails_ready — emitted by the thumbnail worker once all three sizes are persisted
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, Dict

from app.core.logging import get_logger

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
    from app.db.redis import MockRedis, redis_manager
    from app.ws.connection_manager import manager

    envelope = json.dumps({
        "event": job.event_type,
        **job.payload,
    })

    # Deliver to all locally-connected WebSocket clients in the room
    await manager.broadcast_to_local(envelope, job.room_id)
    logger.debug(
        "Broadcast '%s' to room_id=%d (%d local connection(s))",
        job.event_type,
        job.room_id,
        len(manager.active_connections.get(job.room_id, [])),
    )

    # Publish to Redis pub/sub for cross-node fan-out when Redis is available
    redis = redis_manager.get_client()
    if not isinstance(redis, MockRedis):
        channel = f"room:{job.room_id}:events"
        try:
            await redis.publish(channel, envelope)
            logger.debug("Published '%s' to Redis channel '%s'", job.event_type, channel)
        except Exception as exc:
            logger.warning("Redis publish failed for channel '%s': %s", channel, exc)


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
