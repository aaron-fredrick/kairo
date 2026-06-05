import json
from typing import Callable, Any


class RedisEventManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        """
        In Redis mode, subscription is usually NOT in-process.
        This is typically handled by workers/consumers.
        """
        raise NotImplementedError(
            "Use a worker/consumer system for Redis subscriptions"
        )

    async def emit(self, event_name: str, payload: Any) -> None:
        message = json.dumps({
            "event": event_name,
            "payload": payload
        })

        await self.redis.publish(event_name, message)