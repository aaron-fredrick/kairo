from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Maps room_id to a list of active WebSockets
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_id: int) -> None:
        """Accept connection and register websocket under the specific room."""
        await websocket.accept()
        if room_id not in self.active_connections:
            self.active_connections[room_id] = []
            
            # Subscribe to the room's event channel only once
            from app.core.event_bus import event_bus
            async def room_handler(message: str) -> None:
                await self.broadcast_to_local(message, room_id)
            await event_bus.subscribe(f"room:{room_id}:events", room_handler)
            
        self.active_connections[room_id].append(websocket)

    def disconnect(self, websocket: WebSocket, room_id: int) -> None:
        """Remove connection from active connections list."""
        if room_id in self.active_connections:
            if websocket in self.active_connections[room_id]:
                self.active_connections[room_id].remove(websocket)
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send message directly to a single socket."""
        await websocket.send_text(message)

    async def broadcast_to_local(self, message: str, room_id: int) -> None:
        """Broadcast message to all connected clients on this local server instance."""
        if room_id in self.active_connections:
            for connection in self.active_connections[room_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    # Connection might be closed, handled gracefully
                    pass

# Global manager instance
manager = ConnectionManager()
