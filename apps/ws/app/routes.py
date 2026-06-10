from fastapi import APIRouter, WebSocket, WebSocketException, Query
import structlog

from app.auth import get_ws_user_id
from app.connection import ConnectionManager
from app.handlers.connection_handler import ConnectionHandler
from app.handlers.message_handler import MessageHandler
from app.handlers.room_handler import RoomHandler

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# Global connection manager (singleton)
connection_manager = ConnectionManager()


@router.websocket("/rooms/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time room communication.

    Connect with: ws://host/ws/rooms/{room_id}?token={jwt_token}

    Token is extracted from query param on initial connection.
    User is trusted throughout the connection lifetime.

    Events:
    - on_connect: User connects to room
    - on_message: User sends message/event
    - on_disconnect: User disconnects from room
    """
    # Extract user_id from JWT token
    try:
        user_id = await get_ws_user_id(token)
    except WebSocketException as e:
        logger.warning(
            "ws.auth_failed",
            room_id=room_id,
            reason=e.reason,
        )
        await websocket.close(code=e.code, reason=e.reason)
        return

    # Initialize handlers
    connection_handler = ConnectionHandler(connection_manager)
    message_handler = MessageHandler(connection_manager)
    room_handler = RoomHandler(connection_manager)

    # Handle connection
    try:
        await connection_handler.on_connect(websocket, user_id, room_id)

        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            logger.debug(
                "ws.message_received",
                user_id=user_id,
                room_id=room_id,
                message_type=data.get("type"),
            )

            # Route to appropriate handler
            await message_handler.on_message(user_id, room_id, data)

    except WebSocketException:
        # Client-initiated close
        pass
    except Exception as e:
        logger.error(
            "ws.error",
            user_id=user_id,
            room_id=room_id,
            error=str(e),
        )
    finally:
        # Handle disconnection
        await connection_handler.on_disconnect(room_id, user_id, websocket)


# TODO: Add additional WebSocket routes
# @router.websocket("/presence")
# async def presence_websocket(websocket: WebSocket, token: str = Query(...)):
#     """Presence tracking across multiple rooms"""
#     pass

# @router.websocket("/notifications")
# async def notifications_websocket(websocket: WebSocket, token: str = Query(...)):
#     """Personal notifications endpoint"""
#     pass
