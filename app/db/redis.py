from typing import Optional
import redis.asyncio as aioredis
from app.core.config import settings

class RedisManager:
    def __init__(self):
        self.client: Optional[aioredis.Redis] = None

    def connect(self) -> None:
        """Establish Redis connection client."""
        self.client = aioredis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=True
        )

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None

    def get_client(self) -> aioredis.Redis:
        """Retrieve active Redis client instance."""
        if self.client is None:
            self.connect()
        return self.client

# Global Redis manager instance
redis_manager = RedisManager()

async def get_redis() -> aioredis.Redis:
    """Dependency to inject Redis client."""
    return redis_manager.get_client()
