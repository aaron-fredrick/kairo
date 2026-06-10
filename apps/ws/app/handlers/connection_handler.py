import structlog
from fastapi import WebSocket

from app.connection import ConnectionManager

logger = structlog.get_logger(__name__)


class ConnectionHandler:
    """Handles WebSocket connection and disconnection events."""

    def __init__(self, connection_manager: ConnectionManager):
        self.connection_manager = connection_manager

    async def on_connect(self, websocket: WebSocket, user_id: int, room_id: int):
        """Handle new WebSocket connection."""
        # TODO: Verify user has access to room
        # TODO: Load user details from cache/db
        # TODO: Emit event: user.connected to event manager

        logger.info(
            "ws.on_connect",
            user_id=user_id,
            room_id=room_id,
        )

        await self.connection_manager.connect(websocket, room_id, user_id)

        # TODO: Send welcome message to connected user
        # TODO: Broadcast user joined event to room
        # TODO: Send updated room user list to all users in room

    async def on_disconnect(self, room_id: int, user_id: int, websocket: WebSocket):
        """Handle WebSocket disconnection."""
        logger.info(
            "ws.on_disconnect",
            user_id=user_id,
            room_id=room_id,
        )

        self.connection_manager.disconnect(room_id, user_id, websocket)

        # TODO: Emit event: user.disconnected to event manager
        # TODO: Broadcast user left event to room
        # TODO: Send updated room user list to all users in room
        # TODO: Clean up user session data


def get_connection_handler(
    connection_manager: ConnectionManager,
) -> ConnectionHandler:
    """Dependency injection for connection handler."""
    return ConnectionHandler(connection_manager)
