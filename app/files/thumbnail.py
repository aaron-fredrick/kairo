import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import aiofiles

from app.auth.jwt import get_current_user_payload
from app.db.database import get_db
from app.models.upload import Upload
from app.services.thumbnail_service import THUMBNAIL_SIZES, thumbnail_abs_path

router = APIRouter()

@router.get("/{blob_hash}", response_class=Response)
async def serve_thumbnail(
    blob_hash: str,
    size: str = "512",
    db: AsyncSession = Depends(get_db),
    _payload: dict = Depends(get_current_user_payload),
) -> Response:
    """Serve a generated thumbnail image. Authentication is required."""
    if size not in THUMBNAIL_SIZES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid thumbnail size.")
        
    result = await db.execute(select(Upload).where(Upload.hash_id == blob_hash))
    upload: Optional[Upload] = result.scalars().first()
    if not upload or not upload.thumbnails_ready:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail not found or not ready.")

    abs_path = thumbnail_abs_path(blob_hash, size)
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thumbnail file missing from storage.")

    async with aiofiles.open(abs_path, "rb") as fh:
        data = await fh.read()

    return Response(content=data, media_type="image/webp")
