# TODO: vaguely coded, needs cleanup and better error handling, but this is the general idea of how the attachments API will work. It will likely need to be expanded with additional endpoints for listing attachments, deleting attachments, etc.

from fastapi import APIRouter, Depends, Header
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db_session
from app.mediators.message_mediator import MessageMediator
from app.schemas.message import MessageWithAttachmentsResponse
import structlog
from fastapi import APIRouter, Depends, Header, UploadFile, File, HTTPException
from typing import Optional
from app.mediators.upload_mediator import UploadMediator
import structlog


logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/attachments", tags=["Attachments"])

def get_upload_mediator() -> UploadMediator:
    return UploadMediator()

from app.core.security import get_current_user_id
from app.schemas.attachment import ThumbnailSize, UploadResponse, DownloadUrlResponse, ThumbnailResponse, AttachmentResponse


@router.post("/upload/{message_id}", response_model=UploadResponse)
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


@router.get("/download/{attachment_id}", response_model=DownloadUrlResponse)
async def get_download_url(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id),
    mediator: UploadMediator = Depends(get_upload_mediator)
):
    """
    Get a secure presigned URL to download an attachment.
    """
    logger.info("Requesting download URL", attachment_id=attachment_id, user_id=user_id)
    url = await mediator.get_secure_download_url(attachment_id)
    return DownloadUrlResponse(url=url)


@router.get("/{attachment_id}/thumbnail/{size}", response_model=ThumbnailResponse)
async def get_thumbnail(
    attachment_id: str,
    size: ThumbnailSize,
    user_id: int = Depends(get_current_user_id),
    mediator: UploadMediator = Depends(get_upload_mediator)
):
    """
    Get a secure presigned URL for a thumbnail of the attachment.
    """
    logger.info("Requesting thumbnail URL", attachment_id=attachment_id, size=size, user_id=user_id)
    url = await mediator.get_thumbnail_url(attachment_id, size)
    return ThumbnailResponse(size=size, download_url=url)


@router.get("/{attachment_id}", response_model=AttachmentResponse)
async def get_attachment_details(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id),
    mediator: UploadMediator = Depends(get_upload_mediator)
):
    """
    Get details about an attachment, including download URL and available thumbnails.
    """
    logger.info("Requesting attachment details", attachment_id=attachment_id, user_id=user_id)
    details = await mediator.get_attachment_details(attachment_id)
    if not details:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return AttachmentResponse(**details.dict())
