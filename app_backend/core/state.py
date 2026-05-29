from typing import List, Protocol
import time
from app_backend.db.redis import get_redis

class StateManager(Protocol):
    async def set_user_active(self, username: str, expire_time: int) -> None:
        ...

    async def get_active_users(self, limit: int = 50) -> List[str]:
        ...

    async def cleanup_inactive_users(self, current_time: int) -> int:
        ...

    async def count_active_users(self) -> int:
        ...

    async def is_user_active(self, username: str) -> bool:
        ...

    async def increment_room_presence(self, room_id: int, username: str, amount: int = 1) -> int:
        ...

    async def remove_room_presence(self, room_id: int, username: str) -> None:
        ...

    async def get_room_presence_users(self, room_id: int) -> List[str]:
        ...


class RedisStateManager:
    """
    State manager implementation that abstracts away raw Redis commands.
    Automatically uses either aioredis or MockRedis internally.
    """
    
    async def _redis(self):
        return await get_redis()

    async def set_user_active(self, username: str, expire_time: int) -> None:
        client = await self._redis()
        await client.zadd("active_users", {username: expire_time})

    async def get_active_users(self, limit: int = 50) -> List[str]:
        client = await self._redis()
        return await client.zrangebyscore("active_users", min=time.time(), max="+inf", start=0, num=limit)

    async def cleanup_inactive_users(self, current_time: int) -> int:
        client = await self._redis()
        return await client.zremrangebyscore("active_users", "-inf", current_time)

    async def count_active_users(self) -> int:
        client = await self._redis()
        return await client.zcard("active_users")

    async def is_user_active(self, username: str) -> bool:
        client = await self._redis()
        score = await client.zscore("active_users", username)
        if score is None or score < time.time():
            return False
        return True

    async def increment_room_presence(self, room_id: int, username: str, amount: int = 1) -> int:
        client = await self._redis()
        return await client.hincrby(f"room:{room_id}:presence_count", username, amount)

    async def remove_room_presence(self, room_id: int, username: str) -> None:
        client = await self._redis()
        await client.hdel(f"room:{room_id}:presence_count", username)

    async def get_room_presence_users(self, room_id: int) -> List[str]:
        client = await self._redis()
        keys = await client.hkeys(f"room:{room_id}:presence_count")
        if not keys:
            return []
        return [k.decode('utf-8') if isinstance(k, bytes) else k for k in keys]


state_manager = RedisStateManager()

async def get_state_manager() -> StateManager:
    return state_manager
