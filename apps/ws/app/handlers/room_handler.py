import structlog
from typing import List

from app.connection import ConnectionManager

logger = structlog.get_logger(__name__)


class RoomHandler:
    """Handles room-specific events and broadcasts."""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def broadcast_to_room(self, room_id: int, event_type: str, payload: dict):
        """Broadcast event to all users in a room."""
        message = {
            "type": event_type,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "data": payload,
        }

        logger.debug(
            "ws.broadcast_to_room",
            room_id=room_id,
            event_type=event_type,
        )

        await self.connection_manager.broadcast_to_room(room_id, message)

    async def get_room_users(self, room_id: int) -> List[int]:
        """Get list of active users in room."""
        # TODO: Enrich with user details (username, avatar, etc.)
        return self.connection_manager.get_room_users(room_id)

    async def send_room_state(self, room_id: int):
        """Send current room state to all users."""
        # TODO: Get room details
        # TODO: Get active users in room
        # TODO: Get recent messages
        # TODO: Get room settings
        logger.debug(
            "ws.send_room_state",
            room_id=room_id,
        )

        # TODO: Broadcast room state event

    async def notify_user_joined(self, room_id: int, user_id: int):
        """Notify room that user joined."""
        # TODO: Get user details
        payload = {
            "user_id": user_id,
            # TODO: Add user details (username, avatar, etc.)
        }

        await self.broadcast_to_room(room_id, "user.joined", payload)

    async def notify_user_left(self, room_id: int, user_id: int):
        """Notify room that user left."""
        payload = {"user_id": user_id}
        await self.broadcast_to_room(room_id, "user.left", payload)

    async def notify_message_created(
        self, room_id: int, message_id: int, user_id: int, content: str
    ):
        """Notify room of new message."""
        # TODO: Get message details from database
        payload = {
            "message_id": message_id,
            "user_id": user_id,
            "content": content,
            # TODO: Add timestamp, attachments, etc.
        }

        await self.broadcast_to_room(room_id, "message.created", payload)

    async def notify_typing(self, room_id: int, user_id: int, is_typing: bool):
        """Notify room of typing status."""
        payload = {
            "user_id": user_id,
            "is_typing": is_typing,
        }

        await self.broadcast_to_room(room_id, "user.typing", payload)


def get_room_handler(
    connection_manager: ConnectionManager,
) -> RoomHandler:
    """Dependency injection for room handler."""
    return RoomHandler(connection_manager)
