from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_username, get_current_user_payload
from app.auth.dependencies import require_admin_or_moderator
from app.core.logging import get_logger
from app.db.database import get_db
from app.models.room import Room
from app.models.message import Message
from app.models.user import User
from app.db.redis import get_redis
from redis.asyncio import Redis

logger = get_logger(__name__)

router = APIRouter(prefix="/rooms", tags=["rooms"])


class RoomCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoomResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AttachmentResponse(BaseModel):
    attachment_id: int
    blob_hash: str
    filename: str
    mime_type: str
    size_bytes: int
    file_url: str
    thumbnails: dict
    thumbnails_ready: bool

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    sender_username: str
    sender_pfp_urls: Optional[dict] = None
    room_id: int
    created_at: datetime
    attachments: Optional[List[AttachmentResponse]] = None

    class Config:
        from_attributes = True


@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_or_moderator),
) -> RoomResponse:
    """Create a new chat room/channel. Restricted to admins and moderators."""
    logger.debug("Room creation requested by '%s': name='%s'", current_user.username, room_data.name)
    from sqlalchemy import select
    from fastapi import HTTPException
    
    # Check if room name already exists
    result = await db.execute(select(Room).where(Room.name == room_data.name))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room name already exists")
    
    room = Room(name=room_data.name, description=room_data.description)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    
    return RoomResponse.model_validate(room)


@router.get("", response_model=List[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    token_payload: dict = Depends(get_current_user_payload),
) -> List[RoomResponse]:
    """Return all available rooms, filtering system rooms based on JWT role."""
    from app.services.admin_service import SYSTEM_ROOM_ADMIN, SYSTEM_ROOM_MODS
    from app.models.user import UserRole
    
    username = token_payload["sub"]
    role = token_payload.get("role", UserRole.NORMAL.value)
    logger.debug("Room list requested by '%s' with role '%s'", username, role)
    
    from sqlalchemy import select
    result = await db.execute(select(Room))
    rooms = result.scalars().all()
    
    filtered_rooms = []
    for r in rooms:
        if r.name == SYSTEM_ROOM_ADMIN and role != UserRole.ADMIN.value:
            continue
        if r.name == SYSTEM_ROOM_MODS and role not in (UserRole.ADMIN.value, UserRole.MODERATOR.value):
            continue
        filtered_rooms.append(r)
        
    return [RoomResponse.model_validate(r) for r in filtered_rooms]


@router.get("/{room_id}/presence")
async def get_room_presence(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_username: str = Depends(get_current_username),
) -> dict:
    usernames = await redis.hkeys(f"room:{room_id}:presence_count")
    if not usernames:
        return {"users": []}
        
    usernames_decoded = [u.decode('utf-8') if isinstance(u, bytes) else u for u in usernames]
    
    from sqlalchemy import select
    from app.models.user import User
    
    result = await db.execute(select(User).where(User.username.in_(usernames_decoded)))
    users = result.scalars().all()
    
    def _get_pfp_urls(user) -> dict | None:
        if not user.pfp_hash:
            return None
        return {
            "128": f"/pfps/{user.pfp_hash}_128.webp",
            "512": f"/pfps/{user.pfp_hash}_512.webp",
            "1024": f"/pfps/{user.pfp_hash}_1024.webp",
        }
        
    presence_list = []
    for u in users:
        presence_list.append({
            "username": u.username,
            "role": u.role,
            "pfp_urls": _get_pfp_urls(u)
        })
        
    return {"users": presence_list}


@router.get("/{room_id}/messages", response_model=List[MessageResponse])
async def get_room_messages(
    room_id: int,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_username: str = Depends(get_current_username),
) -> List[MessageResponse]:
    """Return the message history for a specific room."""
    logger.debug(
        "Message history requested by '%s' for room_id=%d (limit=%d)",
        current_username,
        room_id,
        limit,
    )
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.services.thumbnail_service import THUMBNAIL_SIZES, thumbnail_url
    from app.models.attachment import Attachment
    
    result = await db.execute(
        select(Message)
        .options(
            selectinload(Message.sender),
            selectinload(Message.attachments).selectinload(Attachment.upload),
        )
        .where(Message.room_id == room_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    
    def _serialize_attachment(att) -> AttachmentResponse:
        upload = att.upload
        return AttachmentResponse(
            attachment_id=att.id,
            blob_hash=upload.hash_id,
            filename=att.filename,
            mime_type=upload.mime_type,
            size_bytes=upload.size_bytes,
            file_url=f"/download/{att.id}",
            thumbnails={
                label: thumbnail_url(upload.hash_id, label)
                for label in THUMBNAIL_SIZES.keys()
            },
            thumbnails_ready=upload.thumbnails_ready,
        )

    def _get_pfp_urls(user) -> Optional[dict]:
        if not user.pfp_hash:
            return None
        return {
            "128": f"/pfps/{user.pfp_hash}_128.webp",
            "512": f"/pfps/{user.pfp_hash}_512.webp",
            "1024": f"/pfps/{user.pfp_hash}_1024.webp",
        }

    return [
        MessageResponse(
            id=m.id,
            content=m.content,
            sender_id=m.sender_id,
            sender_username=m.sender.username,
            sender_pfp_urls=_get_pfp_urls(m.sender),
            room_id=m.room_id,
            created_at=m.created_at,
            attachments=[_serialize_attachment(a) for a in m.attachments] or None,
        ) for m in reversed(messages)
    ]


