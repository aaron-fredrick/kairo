from pydantic import BaseModel

class UploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str

class DownloadUrlResponse(BaseModel):
    url: str
