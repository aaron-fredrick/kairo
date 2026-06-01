import uuid
import os
import json
import structlog
from fastapi import UploadFile, HTTPException
from typing import Optional
from app.core.config import settings
from app.core.redis import get_redis
from app.core.storage import get_boto_client

logger = structlog.get_logger(__name__)

class UploadMediator:
    """
    Mediator for handling file uploads.
    It writes the raw upload to storage in a temporary location,
    pushes an event to Redis, and returns an eventual consistency response.
    """

    async def handle_raw_upload(self, file: UploadFile, user_id: int, idempotency_key: Optional[str] = None) -> 'UploadResponse':
        redis = await get_redis()
        
        # Idempotency Check
        if idempotency_key:
            cache_key = f"upload:idempotency:{user_id}:{idempotency_key}"
            existing = await redis.get(cache_key)
            if existing:
                logger.info("Idempotent upload request matched", user_id=user_id, idempotency_key=idempotency_key)
                return json.loads(existing)

        # Generate unique temporary object name
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        upload_id = str(uuid.uuid4())
        temp_object_name = f"temp/{upload_id}{file_ext}"

        # Write to storage
        boto_client = get_boto_client()
        content = await file.read()
        
        try:
            if settings.STORAGE_BACKEND == "local":
                # Fallback to local
                path = os.path.join(settings.DATA_DIR, "temp", f"{upload_id}{file_ext}")
                with open(path, "wb") as f:
                    f.write(content)
            else:
                boto_client.put_object(
                    Bucket=settings.S3_BUCKET,
                    Key=temp_object_name,
                    Body=content,
                    ContentType=file.content_type
                )
            logger.info("Raw file uploaded to storage", upload_id=upload_id, backend=settings.STORAGE_BACKEND)
        except Exception as e:
            logger.error("Failed to upload file to storage", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to upload file")

        # Add task to Redis queue for the worker service to create blob
        task_data = {
            "upload_id": upload_id,
            "user_id": user_id,
            "temp_path": temp_object_name,
            "filename": file.filename,
            "content_type": file.content_type
        }
        
        try:
            await redis.lpush("queue:process_blob", json.dumps(task_data))
            logger.info("Queued blob processing task", upload_id=upload_id)
        except Exception as e:
            logger.error("Failed to enqueue task", error=str(e))
            raise HTTPException(status_code=500, detail="Failed to queue file processing")

        # Prepare Eventual Consistency Response
        from app.schemas.upload import UploadResponse
        response = UploadResponse(
            upload_id=upload_id,
            status="processing",
            message="Upload complete. File is being processed."
        )

        # Save Idempotency
        if idempotency_key:
            await redis.setex(cache_key, 3600, response.model_dump_json()) # 1 hour TTL

        return response

    async def get_secure_download_url(self, object_name: str) -> str:
        """Get signed URL for attachment download"""
        from app.core.storage import generate_presigned_url
        url = generate_presigned_url(object_name)
        if not url:
            raise HTTPException(status_code=404, detail="Could not generate download link")
        return url
