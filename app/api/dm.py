from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_
from sqlalchemy.orm import joinedload
from datetime import datetime

from app.auth.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.direct_message import DirectMessage

router = APIRouter(prefix="/dm", tags=["dm"])


def check_dm_permission(sender: User, recipient: User) -> bool:
    """
    Check if sender is allowed to DM recipient based on role rules.
    - normal users can dm each other
    - normal users can dm mods but not admins
    - admins can dm anyone
    - mods can dm anyone (implied by lack of restriction)
    """
    if sender.role == UserRole.ADMIN.value:
        return True
    if sender.role == UserRole.MODERATOR.value:
        return True
    
    # Normal user
    if sender.role == UserRole.NORMAL.value:
        if recipient.role == UserRole.ADMIN.value:
            return False
        return True
        
    return False


class DMCreate(BaseModel):
    content: str

class DMResponse(BaseModel):
    id: int
    content: str
    sender_id: int
    sender_username: str
    recipient_id: int
    recipient_username: str
    created_at: datetime


@router.post("/{username}", response_model=DMResponse)
async def send_direct_message(
    username: str,
    message_data: DMCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DMResponse:
    """Send a direct message to a user."""
    result = await db.execute(select(User).where(User.username == username))
    recipient = result.scalars().first()
    
    if not recipient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    if not check_dm_permission(current_user, recipient):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail=f"You do not have permission to direct message users with role '{recipient.role}'"
        )
        
    dm = DirectMessage(
        content=message_data.content,
        sender_id=current_user.id,
        recipient_id=recipient.id
    )
    db.add(dm)
    await db.commit()
    await db.refresh(dm)
    
    return DMResponse(
        id=dm.id,
        content=dm.content,
        sender_id=current_user.id,
        sender_username=current_user.username,
        recipient_id=recipient.id,
        recipient_username=recipient.username,
        created_at=dm.created_at
    )


@router.get("/{username}", response_model=List[DMResponse])
async def get_direct_messages(
    username: str,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DMResponse]:
    """Get direct message history with a user."""
    result = await db.execute(select(User).where(User.username == username))
    other_user = result.scalars().first()
    
    if not other_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Query messages between these two users
    query_result = await db.execute(
        select(DirectMessage)
        .options(joinedload(DirectMessage.sender), joinedload(DirectMessage.recipient))
        .where(
            or_(
                and_(DirectMessage.sender_id == current_user.id, DirectMessage.recipient_id == other_user.id),
                and_(DirectMessage.sender_id == other_user.id, DirectMessage.recipient_id == current_user.id)
            )
        )
        .order_by(DirectMessage.created_at.desc())
        .limit(limit)
    )
    
    messages = query_result.scalars().all()
    
    return [
        DMResponse(
            id=m.id,
            content=m.content,
            sender_id=m.sender_id,
            sender_username=m.sender.username,
            recipient_id=m.recipient_id,
            recipient_username=m.recipient.username,
            created_at=m.created_at
        ) for m in reversed(messages)
    ]
