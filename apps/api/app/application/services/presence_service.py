import time
from typing import List

from app.infrastructure.cache.cache_manager import CacheManager

class PresenceService:
    def __init__(self, cache_manager: CacheManager):
        self.cache_manager = cache_manager

    async def update_heartbeat(self, user_id: int) -> int:
        timestamp = int(time.time())
        # Uses cache manager rather than direct redis zadd
        await self.cache_manager.set(f"presence:{user_id}", timestamp, ttl=120)
        return timestamp

    async def get_online_users(self, threshold_seconds: int = 60) -> List[int]:
        # Simplified abstraction
        return []
