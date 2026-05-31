import redis.asyncio as aioredis
from typing import List

class PresenceService:
    async def set_user_online(self, redis: aioredis.Redis, username: str, room_id: int) -> None:
        """Mark a user as online in a specific room."""
        # TODO: Implement Redis presence tracking logic
        pass

    async def set_user_offline(self, redis: aioredis.Redis, username: str, room_id: int) -> None:
        """Mark a user as offline/disconnected."""
        # TODO: Implement Redis offline state logic
        pass

    async def get_online_users(self, redis: aioredis.Redis, room_id: int) -> List[str]:
        """Fetch list of online users in a room."""
        # TODO: Implement Redis fetch logic
        pass

    async def set_typing(self, redis: aioredis.Redis, username: str, room_id: int, typing: bool) -> None:
        """Track if a user is currently typing in a room."""
        # TODO: Implement typing indicators with short TTLs
        pass

presence_service = PresenceService()
