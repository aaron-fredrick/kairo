import json
import time

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.auth.jwt import decode_access_token
from app.core.logging import get_logger
from app.db.redis import get_redis
from app.services.auth_service import auth_service
from app.ws.connection_manager import manager

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])


@router.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(None),
    redis_client: aioredis.Redis = Depends(get_redis),
) -> None:
    """
    Authenticated WebSocket endpoint for real-time room chat.

    Authentication is performed via a token query parameter. The connection is
    rejected with close code 1008 (policy violation) if the token is absent,
    invalid, or the session has expired in Redis.
    """
    client_host = websocket.client.host if websocket.client else "unknown"

    if not token:
        logger.warning("WS connection rejected (no token): room_id=%d host=%s", room_id, client_host)
        await websocket.close(code=1008)
        return

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        logger.warning("WS connection rejected (invalid token): room_id=%d host=%s", room_id, client_host)
        await websocket.close(code=1008)
        return

    username: str = payload["sub"]

    score = await redis_client.zscore("active_users", username)
    if score is None or score < time.time():
        logger.info(
            "WS connection rejected (session expired): user='%s' room_id=%d", username, room_id
        )
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, room_id)
    await auth_service.refresh_user_activity(redis_client, username)
    logger.info("WS connected: user='%s' room_id=%d host=%s", username, room_id, client_host)

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WS message received from '%s' in room_id=%d", username, room_id)

            try:
                event_data: dict = json.loads(data)
            except json.JSONDecodeError:
                logger.debug("WS invalid JSON from '%s'", username)
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}),
                    websocket,
                )
                continue

            await auth_service.refresh_user_activity(redis_client, username)
            event_data["sender"] = username
            await manager.broadcast_to_local(json.dumps(event_data), room_id)

    except WebSocketDisconnect:
        manager.disconnect(websocket, room_id)
        logger.info("WS disconnected: user='%s' room_id=%d", username, room_id)
