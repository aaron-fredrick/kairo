from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user_payload
from app.db.database import get_db
from app.models.attachment import Attachment
from app.storage.blob_manager import blob_manager

router = APIRouter()


@router.get("/{attachment_id}", response_class=Response)
async def download_file(
    attachment_id: int,
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    """
    Serve raw blob bytes for download.

    The URL is keyed by attachment_id (not blob_hash) so the response carries
    the correct user-facing filename. Authentication is required.
    """
    result = await db.execute(
        select(Attachment)
        .options(joinedload(Attachment.upload))
        .where(Attachment.id == attachment_id)
    )
    attachment: Optional[Attachment] = result.scalars().first()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found.")

    upload = attachment.upload
    try:
        data = await blob_manager.get_blob(upload.hash_id)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Blob data missing from storage.")

    headers = {
        "Content-Disposition": f'attachment; filename="{attachment.filename}"'
    }
    return Response(content=data, media_type=upload.mime_type, headers=headers)
