from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from app.ws.connection_manager import manager
from app.db.redis import get_redis
from app.auth.jwt import decode_access_token
from app.services.auth_service import auth_service
import redis.asyncio as aioredis
import json
import time

router = APIRouter(prefix="/ws", tags=["websockets"])

@router.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    room_id: int, 
    token: str = Query(None),
    redis_client: aioredis.Redis = Depends(get_redis)
):
    """Handle incoming websocket connection, receive events, and handle client disconnection."""
    if not token:
        await websocket.close(code=1008)
        return
        
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        await websocket.close(code=1008)
        return
        
    username = payload["sub"]
    
    # Check if user is active in Redis
    current_time = time.time()
    score = await redis_client.zscore("active_users", username)
    if score is None or score < current_time:
        await websocket.close(code=1008)
        return
        
    await manager.connect(websocket, room_id)
    await auth_service.refresh_user_activity(redis_client, username)
    try:
        while True:
            # Wait for any message from the client
            data = await websocket.receive_text()
            
            # TODO: Parse event data, validate authentication, store in DB, publish to Redis
            # Example message format expected: {"event": "message", "content": "hello"}
            try:
                event_data = json.loads(data)
                
                # Refresh activity on message
                await auth_service.refresh_user_activity(redis_client, username)
                
                # Add sender info
                event_data["sender"] = username
                
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
