from fastapi import APIRouter, Depends, Header, UploadFile, File, HTTPException
from typing import Optional
import structlog

from app.api.dependencies.auth import get_current_user_id
from app.api.dependencies.services import get_attachment_service
from app.schemas.attachment_schema import (
    ThumbnailSize,
    UploadResponseSchema,
    DownloadUrlResponseSchema,
    ThumbnailResponseSchema,
    AttachmentResponseSchema,
)
from app.application.services.attachment_service import AttachmentService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/attachments", tags=["Attachments"])


@router.post("/upload/{message_id}", response_model=UploadResponseSchema)
async def upload_file(
    message_id: int,
    file: UploadFile = File(...),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    user_id: int = Depends(get_current_user_id),
    service: AttachmentService = Depends(get_attachment_service),
):
    """Upload file to message. User must be message author."""
    result = await service.upload_file(file, message_id, user_id, idempotency_key)
    return UploadResponseSchema(**result)


@router.get("/download/{attachment_id}", response_model=DownloadUrlResponseSchema)
async def get_download_url(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id),
    service: AttachmentService = Depends(get_attachment_service),
):
    """Get presigned download URL for attachment."""
    result = await service.download_attachment(attachment_id, user_id)
    return DownloadUrlResponseSchema(**result)


@router.get("/{attachment_id}/thumbnail/{size}", response_model=ThumbnailResponseSchema)
async def get_thumbnail(
    attachment_id: str,
    size: ThumbnailSize,
    user_id: int = Depends(get_current_user_id),
    service: AttachmentService = Depends(get_attachment_service),
):
    """Get thumbnail URL for attachment."""
    result = await service.get_thumbnail(attachment_id, size, user_id)
    return ThumbnailResponseSchema(**result)


@router.get("/{attachment_id}", response_model=AttachmentResponseSchema)
async def get_attachment_details(
    attachment_id: str,
    user_id: int = Depends(get_current_user_id),
    service: AttachmentService = Depends(get_attachment_service),
):
    """Get attachment metadata including download URL and thumbnails."""
    result = await service.get_attachment_details(attachment_id, user_id)
    return AttachmentResponseSchema(**result)
