import structlog
from typing import Dict, Set

from app.connection import ConnectionManager
from app.handlers.connection_handler import ConnectionHandler
from app.handlers.message_handler import MessageHandler
from app.handlers.room_handler import RoomHandler

logger = structlog.get_logger(__name__)


class WebSocketManager:
    """Central manager for WebSocket operations and coordination."""

    def __init__(self):
        self.connection_manager = ConnectionManager()
        self.connection_handler = ConnectionHandler(self.connection_manager)
        self.message_handler = MessageHandler(self.connection_manager)
        self.room_handler = RoomHandler(self.connection_manager)

    # TODO: Add methods for:
    # - Event subscription and publishing
    # - Message queuing for offline users
    # - Presence tracking
    # - Room state synchronization
    # - Client message validation
    # - Rate limiting per user/room

    def get_connection_manager(self) -> ConnectionManager:
        """Get connection manager instance."""
        return self.connection_manager

    def get_connection_handler(self) -> ConnectionHandler:
        """Get connection handler instance."""
        return self.connection_handler

    def get_message_handler(self) -> MessageHandler:
        """Get message handler instance."""
        return self.message_handler

    def get_room_handler(self) -> RoomHandler:
        """Get room handler instance."""
        return self.room_handler


# Global WebSocket manager instance
ws_manager = WebSocketManager()


def get_ws_manager() -> WebSocketManager:
    """Dependency injection for WebSocket manager."""
    return ws_manager
