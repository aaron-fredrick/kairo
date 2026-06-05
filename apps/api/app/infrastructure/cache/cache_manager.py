from typing import Any, Optional

from .local_cache_manager import LocalCacheManager
from .redis_cache_manager import RedisCacheManager


class CacheManager:

    def __init__(
        self,
        local_cache: LocalCacheManager,
        redis_cache: Optional[RedisCacheManager] = None,
    ):
        self.local_cache = local_cache
        self.redis_cache = redis_cache

    async def get(self, key: str) -> Any | None:

        value = await self.local_cache.get(key)

        if value is None and self.redis_cache:
            value = await self.redis_cache.get(key)

        return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> None:

        await self.local_cache.set(
            key=key,
            value=value,
            ttl=int(ttl / 2) if ttl else None,
        )
        
        if self.redis_cache:
            await self.redis_cache.set(
                key=key,
                value=value,
                ttl=ttl,
            )

    async def delete(self, key: str) -> None:

        await self.local_cache.delete(key)
        
        if self.redis_cache:
            await self.redis_cache.delete(key)

    async def exists(self, key: str) -> bool:

        return (
            await self.local_cache.exists(key)
            or (self.redis_cache and await self.redis_cache.exists(key))
        )