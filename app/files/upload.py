import os
import uuid
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.auth.jwt import get_current_user_payload
from app.core.config import settings
import aiofiles

router = APIRouter()

@router.post("", status_code=status.HTTP_201_CREATED)
async def pre_upload_file(
    file: UploadFile,
    room_id: int = 0,
    _payload: dict = Depends(get_current_user_payload),
) -> dict:
    """
    Accept an upload and store it temporarily in data/temp/uploads/.
    Returns a unique upload_id to be attached to a WebSocket message.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    upload_id = f"upload_{uuid.uuid4().hex}"
    temp_dir = settings.TEMP_UPLOAD_DIR
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, upload_id)

    bytes_written = 0
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024

    try:
        async with aiofiles.open(temp_path, "wb") as f:
            while chunk := await file.read(256 * 1024):
                bytes_written += len(chunk)
                if bytes_written > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds max size of {settings.UPLOAD_MAX_SIZE_MB}MB",
                    )
                await f.write(chunk)
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=str(e))

    mime_type = file.content_type
    if not mime_type or mime_type == "application/octet-stream":
        mime_type, _ = mimetypes.guess_type(file.filename)
        mime_type = mime_type or "application/octet-stream"

    return {
        "upload_id": upload_id,
        "original_filename": file.filename,
        "mime_type": mime_type,
        "size_bytes": bytes_written,
        "room_id": room_id,
    }
