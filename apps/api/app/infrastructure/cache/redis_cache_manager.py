import json
from typing import Any

from redis.asyncio import Redis

from .protocol import CacheProtocol


class RedisCacheManager:

    def __init__(self, redis: Redis):
        self.redis = redis

    async def get(self, key: str) -> Any | None:
        value = await self.redis.get(key)

        if value is None:
            return None

        return json.loads(value)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:

        payload = json.dumps(value)

        if ttl is not None:
            await self.redis.set(key, payload, ex=ttl)
        else:
            await self.redis.set(key, payload)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self.redis.exists(key))