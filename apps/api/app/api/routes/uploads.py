from fastapi import APIRouter, Depends, Header, UploadFile, File, HTTPException
from typing import Optional
from app.services.upload_mediator import UploadMediator
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/uploads", tags=["Uploads"])

def get_upload_mediator() -> UploadMediator:
    return UploadMediator()

from app.core.security import get_current_user_id
from app.schemas.upload import UploadResponse, DownloadUrlResponse

@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user_id: int = Depends(get_current_user_id),
    mediator: UploadMediator = Depends(get_upload_mediator)
):
    """
    Upload a file. This writes to raw storage and queues it for the worker to create a blob.
    """
    logger.info("Received file upload request", filename=file.filename, user_id=user_id)
    return await mediator.handle_raw_upload(file, user_id, idempotency_key)

@router.get("/download/{object_name}", response_model=DownloadUrlResponse)
async def get_download_url(
    object_name: str,
    user_id: int = Depends(get_current_user_id),
    mediator: UploadMediator = Depends(get_upload_mediator)
):
    """
    Get a secure presigned URL to download an attachment.
    """
    logger.info("Requesting download URL", object_name=object_name, user_id=user_id)
    url = await mediator.get_secure_download_url(object_name)
    return DownloadUrlResponse(url=url)
