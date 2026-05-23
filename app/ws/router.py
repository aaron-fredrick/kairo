from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from app.ws.connection_manager import manager
from app.db.redis import get_redis
import redis.asyncio as aioredis
import json

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: int, 
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Handle incoming websocket connection, receive events, and handle client disconnection."""
    await manager.connect(websocket, room_id)
    try:
        while True:
            # Wait for any message from the client
            data = await websocket.receive_text()
            
            # TODO: Parse event data, validate authentication, store in DB, publish to Redis
            # Example message format expected: {"event": "message", "content": "hello"}
            try:
                event_data = json.loads(data)
                # For now, echo the message locally as placeholder
                await manager.broadcast_to_local(json.dumps(event_data), room_id)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}), 
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        # TODO: Handle offline presence updating
