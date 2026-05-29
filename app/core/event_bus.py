import asyncio
from collections import defaultdict
from typing import Callable, Awaitable, Dict, List, Protocol
import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger
from app.db.redis import redis_manager

logger = get_logger(__name__)

class EventBus(Protocol):
    async def publish(self, channel: str, message: str) -> None:
        ...

    async def subscribe(self, channel: str, handler: Callable[[str], Awaitable[None]]) -> None:
        ...

    async def close(self) -> None:
        ...

class LocalEventBus:
    """In-memory event bus for local deployment without Redis."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[str], Awaitable[None]]]] = defaultdict(list)

    async def publish(self, channel: str, message: str) -> None:
        logger.debug("LocalEventBus: publishing to channel '%s'", channel)
        if channel not in self._subscribers:
            return
        for handler in self._subscribers[channel]:
            # Await in-process handlers so TestClient/WS tests receive messages reliably.
            await handler(message)

    async def subscribe(self, channel: str, handler: Callable[[str], Awaitable[None]]) -> None:
        logger.debug("LocalEventBus: subscribing to channel '%s'", channel)
        self._subscribers[channel].append(handler)

    async def close(self) -> None:
        self._subscribers.clear()

class RedisEventBus:
    """Redis Pub/Sub event bus for horizontally scalable deployment."""
    def __init__(self):
        self.pubsub: aioredis.client.PubSub | None = None
        self._handlers: Dict[str, List[Callable[[str], Awaitable[None]]]] = defaultdict(list)
        self._listen_task: asyncio.Task | None = None

    @property
    def redis(self) -> aioredis.Redis:
        # We assume USE_REDIS is True if EVENT_BUS=redis
        client = redis_manager.get_client()
        return client

    async def publish(self, channel: str, message: str) -> None:
        logger.debug("RedisEventBus: publishing to channel '%s'", channel)
        await self.redis.publish(channel, message)

    async def subscribe(self, channel: str, handler: Callable[[str], Awaitable[None]]) -> None:
        logger.debug("RedisEventBus: subscribing to channel '%s'", channel)
        if self.pubsub is None:
            self.pubsub = self.redis.pubsub()
            self._listen_task = asyncio.create_task(self._listen())

        if channel not in self._handlers:
            await self.pubsub.subscribe(channel)

        self._handlers[channel].append(handler)

    async def _listen(self):
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = message["data"]
                    
                    if isinstance(channel, bytes):
                        channel = channel.decode()
                    if isinstance(data, bytes):
                        data = data.decode()

                    if channel in self._handlers:
                        for handler in self._handlers[channel]:
                            asyncio.create_task(handler(data))
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("RedisEventBus listen error: %s", exc)

    async def close(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
        if self.pubsub:
            await self.pubsub.close()
        self._handlers.clear()

def get_event_bus() -> EventBus:
    if settings.EVENT_BUS == "redis":
        return RedisEventBus()
    return LocalEventBus()

event_bus = get_event_bus()
