from typing import Dict, Literal
from uuid import UUID
from pydantic import Field, BaseModel

from .common_schema import APIBaseSchema


ThumbnailSize = Literal[128, 512, 1024]


class ThumbnailResponseSchema(APIBaseSchema):
    size: ThumbnailSize
    download_url: str


class AttachmentResponseSchema(APIBaseSchema):
    id: UUID
    filename: str
    content_type: str
    size_bytes: int
    download_url: str
    thumbnails: Dict[ThumbnailSize, str] = Field(default_factory=dict)
    

class UploadResponseSchema(BaseModel):
    upload_id: str
    status: str
    message: str

class DownloadUrlResponseSchema(BaseModel):
    url: str
