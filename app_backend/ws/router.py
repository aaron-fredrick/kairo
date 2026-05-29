import asyncio
import json
import time
from typing import Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app_backend.auth.jwt import decode_access_token
from app_backend.core.logging import get_logger
from app_backend.db.database import get_db, AsyncSessionLocal
from app_backend.core.state import get_state_manager, StateManager
from app_backend.models.user import User, UserRole
from app_backend.models.message import Message
from app_backend.services.auth_service import auth_service
from app_backend.services.admin_service import SYSTEM_ROOM_ADMIN, SYSTEM_ROOM_MODS
from app_backend.ws.connection_manager import manager

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websockets"])

# Maps system room names to the minimum role required to access them.
_SYSTEM_ROOM_ACCESS: dict[str, set[str]] = {
    SYSTEM_ROOM_ADMIN: {UserRole.ADMIN.value},
    SYSTEM_ROOM_MODS: {UserRole.ADMIN.value, UserRole.MODERATOR.value},
}


async def _resolve_room_name(room_id: int, db: AsyncSession) -> Optional[str]:
    """Return the room name for the given id, or None if not found."""
    from app_backend.models.room import Room
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalars().first()
    return room.name if room else None


def _is_room_access_denied(room_name: Optional[str], role: str) -> bool:
    """Return True when the user's role is not permitted to enter the room."""
    if room_name is None:
        return False
    required_roles = _SYSTEM_ROOM_ACCESS.get(room_name)
    if required_roles is None:
        return False
    return role not in required_roles


@router.websocket("/chat/{room_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: int,
    token: str = Query(None),
    state: StateManager = Depends(get_state_manager),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Authenticated WebSocket endpoint for real-time room chat.

    Authentication is performed via a token query parameter. The connection is
    rejected with close code 1008 (policy violation) if the token is absent,
    invalid, the session has expired, or the user's role does not grant access
    to the requested room (applies to the 'admins' and 'moderators' rooms).
    """
    client_host = websocket.client.host if websocket.client else "unknown"

    if not token:
        logger.warning("WS rejected (no token): room_id=%d host=%s", room_id, client_host)
        await websocket.close(code=1008)
        return

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        logger.warning("WS rejected (invalid token): room_id=%d host=%s", room_id, client_host)
        await websocket.close(code=1008)
        return

    username: str = payload["sub"]
    role: str = payload.get("role", UserRole.NORMAL.value)

    is_active = await state.is_user_active(username)
    if not is_active:
        logger.info("WS rejected (session expired): user='%s' room_id=%d", username, room_id)
        await websocket.close(code=1008)
        return

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalars().first()
    if not user:
        logger.warning("WS rejected (user not found in DB): username='%s'", username)
        await websocket.close(code=1008)
        return
    sender_id = user.id

    # Enforce system-room access control.
    room_name = await _resolve_room_name(room_id, db)
    if room_name is None:
        logger.warning("WS rejected (room not found): room_id=%d", room_id)
        await websocket.close(code=1008)
        return

    if _is_room_access_denied(room_name, role):
        logger.warning(
            "WS rejected (insufficient role): user='%s' role='%s' room='%s'",
            username,
            role,
            room_name,
        )
        await websocket.close(code=1008)
        return

    await manager.connect(websocket, room_id)
    await auth_service.refresh_user_activity(state, username)
    logger.info("WS connected: user='%s' role='%s' room_id=%d host=%s", username, role, room_id, client_host)

    # Track presence count and broadcast if this is the first connection for the user in this room
    count = await state.increment_room_presence(room_id, username, 1)
    if count == 1:
        pfp_urls = None
        if user.pfp_hash:
            pfp_urls = {
                "128": f"/api/data/pfp?hash={user.pfp_hash}&size=128",
                "512": f"/api/data/pfp?hash={user.pfp_hash}&size=512",
                "1024": f"/api/data/pfp?hash={user.pfp_hash}&size=1024",
            }
        from app_backend.core.event_bus import event_bus
        asyncio.create_task(event_bus.publish(f"room:{room_id}:events", json.dumps({
            "event": "presence_update",
            "action": "join",
            "username": username,
            "role": role,
            "pfp_urls": pfp_urls,
        })))

    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("WS message from '%s' in room_id=%d", username, room_id)

            try:
                event_data: dict = json.loads(data)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}),
                    websocket,
                )
                continue

            await auth_service.refresh_user_activity(state, username)
            
            content = event_data.get("content")
            incoming_attachments: list[dict] | None = event_data.get("attachments")

            if content or incoming_attachments:
                async with AsyncSessionLocal() as session:
                    # Create the message first so we have a message_id for attachments
                    message = Message(
                        sender_id=sender_id,
                        room_id=room_id,
                        content=content or "",
                    )
                    session.add(message)
                    await session.flush()  # populate message.id

                    attachments_data = []
                    thumbnail_jobs = []
                    if incoming_attachments:
                        from app_backend.services.upload_service import confirm_upload

                        # Sequential: AsyncSession cannot be shared across concurrent coroutines
                        for att in incoming_attachments:
                            res, job = await confirm_upload(
                                upload_id=att.get("upload_id", ""),
                                original_filename=att.get("filename", ""),
                                mime_type=att.get("mime_type", ""),
                                size_bytes=att.get("size_bytes", 0),
                                message_id=message.id,
                                room_id=room_id,
                                db=session,
                            )
                            if res:
                                attachments_data.append(res)
                            if job:
                                thumbnail_jobs.append(job)

                    await session.commit()
                    await session.refresh(message)

                    event_data["id"] = message.id
                    if message.created_at:
                        event_data["created_at"] = message.created_at.isoformat()
                    else:
                        from datetime import datetime
                        event_data["created_at"] = datetime.utcnow().isoformat()

                    if attachments_data:
                        event_data["attachments"] = attachments_data

                event_data["event"] = "new_message"

            event_data["sender"] = username
            event_data["role"] = role
            
            # Fetch sender_pfp_urls
            async with AsyncSessionLocal() as session:
                user_res = await session.execute(select(User).where(User.username == username))
                user = user_res.scalars().first()
                if user and user.pfp_hash:
                    event_data["sender_pfp_urls"] = {
                        "128": f"/api/data/pfp?hash={user.pfp_hash}&size=128",
                        "512": f"/api/data/pfp?hash={user.pfp_hash}&size=512",
                        "1024": f"/api/data/pfp?hash={user.pfp_hash}&size=1024",
                    }
                else:
                    event_data["sender_pfp_urls"] = None

            from app_backend.core.event_bus import event_bus
            await event_bus.publish(f"room:{room_id}:events", json.dumps(event_data))

            # Enqueue thumbnail jobs AFTER the message is broadcast to clients,
            # preventing a race condition where the 'thumbnails_ready' event 
            # beats the 'new_message' event.
            if content or incoming_attachments:
                from app_backend.workers.thumbnail import thumbnail_queue
                for job in thumbnail_jobs:
                    await thumbnail_queue.put(job)

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, room_id)
        count = await state.increment_room_presence(room_id, username, -1)
        if count <= 0:
            await state.remove_room_presence(room_id, username)
            from app_backend.core.event_bus import event_bus
            asyncio.create_task(event_bus.publish(f"room:{room_id}:events", json.dumps({
                "event": "presence_update",
                "action": "leave",
                "username": username,
            })))
