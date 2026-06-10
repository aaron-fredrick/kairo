from dataclasses import dataclass
from datetime import datetime


@dataclass
class UploadDTO:
    id: int
    original_filename: str
    extension: str
    mime_type: str
    size_bytes: int
    hash_id: str
    storage_backend: str
    storage_path: str
    file_sha256: str
    thumbnails_ready: bool
    thumbnail_sha256_sm: str | None
    thumbnail_sha256_md: str | None
    thumbnail_sha256_lg: str | None
    created_at: datetime
    updated_at: datetime
