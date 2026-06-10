import structlog
from typing import Dict, Any

from app.connection import ConnectionManager

logger = structlog.get_logger(__name__)


class MessageHandler:
    """Handles WebSocket message events."""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def on_message(
        self,
        user_id: int,
        room_id: int,
        message_data: Dict[str, Any],
    ):
        """Handle incoming WebSocket message."""
        # TODO: Validate message structure
        # TODO: Check user permissions to send message in room
        # TODO: Save message to database via repository
        # TODO: Emit event: message.created to event manager

        message_type = message_data.get("type")
        logger.info(
            "ws.on_message",
            user_id=user_id,
            room_id=room_id,
            message_type=message_type,
        )

        # TODO: Route to specific message type handler
        if message_type == "chat":
            await self._handle_chat_message(user_id, room_id, message_data)
        elif message_type == "typing":
            await self._handle_typing_indicator(user_id, room_id, message_data)
        elif message_type == "reaction":
            await self._handle_reaction(user_id, room_id, message_data)
        else:
            logger.warning(
                "ws.unknown_message_type",
                user_id=user_id,
                room_id=room_id,
                message_type=message_type,
            )

    async def _handle_chat_message(
        self, user_id: int, room_id: int, message_data: Dict[str, Any]
    ):
        """Handle chat message."""
        # TODO: Extract message content
        # TODO: Verify attachment IDs if present
        # TODO: Create message record in database
        # TODO: Broadcast message to room
        logger.debug(
            "ws.handle_chat_message",
            user_id=user_id,
            room_id=room_id,
        )

    async def _handle_typing_indicator(
        self, user_id: int, room_id: int, message_data: Dict[str, Any]
    ):
        """Handle typing indicator."""
        # TODO: Broadcast typing status to room
        logger.debug(
            "ws.handle_typing_indicator",
            user_id=user_id,
            room_id=room_id,
        )

    async def _handle_reaction(
        self, user_id: int, room_id: int, message_data: Dict[str, Any]
    ):
        """Handle message reaction."""
        # TODO: Validate message_id
        # TODO: Save reaction to database
        # TODO: Broadcast reaction to room
        logger.debug(
            "ws.handle_reaction",
            user_id=user_id,
            room_id=room_id,
        )


def get_message_handler(
    connection_manager: ConnectionManager,
) -> MessageHandler:
    """Dependency injection for message handler."""
    return MessageHandler(connection_manager)
