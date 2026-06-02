from typing import Dict, Literal
from uuid import UUID
from pydantic import Field, BaseModel

from .common import APIBaseSchema


ThumbnailSize = Literal[128, 512, 1024]


# GET /api/attachments/{attachment_id}/thumbnail/{size}
class ThumbnailResponse(APIBaseSchema):
    size: ThumbnailSize
    download_url: str


# GET /api/attachments/{attachment_id}
class AttachmentResponse(APIBaseSchema):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    download_url: str
    thumbnails: Dict[ThumbnailSize, str] = Field(default_factory=dict)
    

class UploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str

class DownloadUrlResponse(BaseModel):
    url: str
