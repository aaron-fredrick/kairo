from fastapi import WebSocket
from typing import Dict, Set
import structlog

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections grouped by room."""

    def __init__(self):
        # room_id -> set of (user_id, websocket) tuples
        self.active_connections: Dict[int, Set[tuple]] = {}

    async def connect(self, websocket: WebSocket, room_id: int, user_id: int):
        """Register new WebSocket connection to room."""
        await websocket.accept()

        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        self.active_connections[room_id].add((user_id, websocket))

        logger.info(
            "ws.user_connected",
            user_id=user_id,
            room_id=room_id,
            total_in_room=len(self.active_connections[room_id]),
        )

    def disconnect(self, room_id: int, user_id: int, websocket: WebSocket):
        """Unregister WebSocket connection from room."""
        if room_id in self.active_connections:
            self.active_connections[room_id].discard((user_id, websocket))

            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

        logger.info(
            "ws.user_disconnected",
            user_id=user_id,
            room_id=room_id,
        )

    async def broadcast_to_room(self, room_id: int, message: dict):
        """Broadcast message to all users in a room."""
        if room_id not in self.active_connections:
            return

        disconnected = []

        for user_id, websocket in self.active_connections[room_id]:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(
                    "ws.broadcast_failed",
                    user_id=user_id,
                    room_id=room_id,
                    error=str(e),
                )
                disconnected.append((user_id, websocket))

        # Clean up disconnected websockets
        for user_id, websocket in disconnected:
            self.disconnect(room_id, user_id, websocket)

    def get_room_users(self, room_id: int) -> list:
        """Get list of user IDs in room."""
        if room_id not in self.active_connections:
            return []

        return [user_id for user_id, _ in self.active_connections[room_id]]
