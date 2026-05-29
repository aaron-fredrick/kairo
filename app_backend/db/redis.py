from typing import Optional, Dict, List, Union
import redis.asyncio as aioredis
from app_backend.core.config import settings

class MockRedis:
    """In-memory mock for Redis when USE_REDIS is False."""
    def __init__(self):
        self._zsets: Dict[str, Dict[str, float]] = {}
        self._hashes: Dict[str, Dict[str, int]] = {}

    async def close(self):
        pass

    async def zadd(self, name: str, mapping: dict) -> int:
        if name not in self._zsets:
            self._zsets[name] = {}
        added = 0
        for k, v in mapping.items():
            if k not in self._zsets[name]:
                added += 1
            self._zsets[name][k] = float(v)
        return added

    async def zscore(self, name: str, value: str) -> Optional[float]:
        if name not in self._zsets:
            return None
        return self._zsets[name].get(value)

    async def zcard(self, name: str) -> int:
        if name not in self._zsets:
            return 0
        return len(self._zsets[name])

    async def zremrangebyscore(self, name: str, min: Union[str, float], max: Union[str, float]) -> int:
        if name not in self._zsets:
            return 0
        
        min_val = float('-inf') if min == "-inf" else float(min)
        max_val = float('inf') if max == "+inf" or max == "inf" else float(max)
        
        to_remove = []
        for k, v in self._zsets[name].items():
            if min_val <= v <= max_val:
                to_remove.append(k)
        
        for k in to_remove:
            del self._zsets[name][k]
            
        return len(to_remove)

    async def zrangebyscore(self, name: str, min: Union[str, float], max: Union[str, float], start: int = 0, num: int = -1) -> List[str]:
        if name not in self._zsets:
            return []
        
        min_val = float('-inf') if min == "-inf" else float(min)
        max_val = float('inf') if max == "+inf" or max == "inf" else float(max)
        
        items = []
        for k, v in self._zsets[name].items():
            if min_val <= v <= max_val:
                items.append((k, v))
                
        items.sort(key=lambda x: x[1])
        
        result = [k for k, v in items]
        if num == -1:
            return result[start:]
        return result[start:start+num]

    async def hincrby(self, name: str, key: str, amount: int = 1) -> int:
        if name not in self._hashes:
            self._hashes[name] = {}
        if key not in self._hashes[name]:
            self._hashes[name][key] = 0
        self._hashes[name][key] += amount
        return self._hashes[name][key]

    async def hkeys(self, name: str) -> List[str]:
        if name not in self._hashes:
            return []
        return list(self._hashes[name].keys())

    async def hdel(self, name: str, *keys: str) -> int:
        if name not in self._hashes:
            return 0
        deleted = 0
        for key in keys:
            if key in self._hashes[name]:
                del self._hashes[name][key]
                deleted += 1
        if not self._hashes[name]:
            del self._hashes[name]
        return deleted

class RedisManager:
    def __init__(self):
        self.client: Optional[Union[aioredis.Redis, MockRedis]] = None

    def connect(self) -> None:
        """Establish Redis connection client."""
        if settings.USE_REDIS:
            self.client = aioredis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True
            )
        else:
            self.client = MockRedis()

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None

    def get_client(self) -> Union[aioredis.Redis, MockRedis]:
        """Retrieve active Redis client instance."""
        if self.client is None:
            self.connect()
        return self.client

# Global Redis manager instance
redis_manager = RedisManager()

async def get_redis() -> Union[aioredis.Redis, MockRedis]:
    """Dependency to inject Redis client."""
    return redis_manager.get_client()
