from app.core.config import settings
from app.infrastructure.cache.cache_manager import CacheManager
from app.infrastructure.cache.local_cache_manager import LocalCacheManager
from app.infrastructure.cache.redis_cache_manager import RedisCacheManager
from app.infrastructure.events.local_event_manager import LocalEventManager
from app.infrastructure.events.redis_event_manager import RedisEventManager


class AppContainer:
    """
    Composition root. Wired once at startup inside FastAPI lifespan.
    Holds all infrastructure singletons that outlive a single request.
    """

    def __init__(self):
        self.redis = None

        # Cache: local is always present; Redis is bolted on if configured.
        local_cache = LocalCacheManager()
        self.cache_manager = CacheManager(local_cache=local_cache)

        # Events: single backend — never hybrid.
        if settings.REDIS_URL:
            import redis.asyncio as aioredis
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            self.event_manager = RedisEventManager(redis_client=self.redis)
            self.cache_manager.redis_cache = RedisCacheManager(redis=self.redis)
        else:
            self.event_manager = LocalEventManager()

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
