import hashlib
import structlog
from typing import List, Optional
from fastapi import UploadFile, HTTPException
import os

from app.core.exceptions import NotFoundError, ForbiddenError
from app.domain.models.attachment_domain import AttachmentDomain
from app.infrastructure.dtos.attachment_dto import AttachmentDTO
from app.infrastructure.dtos.upload_dto import UploadDTO
from app.infrastructure.repositories.attachment_repository import AttachmentRepository
from app.infrastructure.repositories.message_repository import MessageRepository
from app.infrastructure.repositories.upload_repository import UploadRepository
from app.infrastructure.cache.cache_manager import CacheManager
from app.infrastructure.storage.storage_client import StorageClient
from app.domain.policies.message_policy import MessagePolicy
from app.infrastructure.events.protocol import EventProtocol

logger = structlog.get_logger(__name__)

TEMP_DIR = "data/temp"
CHUNK_SIZE = 8192  # 8KB chunks for hashing and upload


class AttachmentService:
    def __init__(
        self,
        attachment_repo: AttachmentRepository,
        message_repo: MessageRepository,
        upload_repo: UploadRepository,
        cache_manager: CacheManager,
        storage_client: StorageClient,
        message_policy: MessagePolicy,
        event_protocol: EventProtocol,
    ):
        self.attachment_repo = attachment_repo
        self.message_repo = message_repo
        self.upload_repo = upload_repo
        self.cache_manager = cache_manager
        self.storage_client = storage_client
        self.message_policy = message_policy
        self.event_protocol = event_protocol

    async def upload_file(
        self,
        file: UploadFile,
        message_id: int,
        user_id: int,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Upload file to message. User must be message author.
        File is saved to temp, event emitted for async worker.
        """
        # Step 1: Verify message exists
        message_dto = await self.message_repo.get_by_id(message_id)
        if not message_dto:
            logger.error(
                "attachment.upload_failed",
                user_id=user_id,
                message_id=message_id,
                error_code="not_found",
                reason="message_not_found",
            )
            raise NotFoundError(f"Message {message_id} not found")

        # Step 2: Verify user is message author
        if message_dto.sender_id != user_id:
            logger.warning(
                "attachment.upload_failed",
                user_id=user_id,
                message_id=message_id,
                error_code="forbidden",
                reason="user_not_message_author",
            )
            raise ForbiddenError("Only message author can add attachments")

        # Step 3: Idempotency check
        if idempotency_key:
            cache_key = f"upload_idempotent:{idempotency_key}"
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.info(
                    "attachment.upload_idempotent_hit",
                    user_id=user_id,
                    message_id=message_id,
                    idempotency_key=idempotency_key,
                    upload_id=cached_result,
                )
                return {
                    "upload_id": str(cached_result),
                    "status": "pending",
                    "message": "File queued for processing (cached)",
                }

        # Step 4: Compute file hash and metadata
        file_content = await file.read()
        file_sha256 = hashlib.sha256(file_content).hexdigest()
        await file.seek(0)  # Reset for storage operation

        extension = os.path.splitext(file.filename)[1].lstrip(".") or "bin"
        mime_type = file.content_type or "application/octet-stream"
        size_bytes = len(file_content)
        hash_id = hashlib.sha256(
            f"{file_sha256}_{int(__import__('time').time())}".encode()
        ).hexdigest()[:16]

        # Step 5: Check for duplicate (content-addressed storage)
        existing_upload = await self.upload_repo.get_by_hash(file_sha256)
        if existing_upload:
            logger.info(
                "attachment.upload_deduplicated",
                user_id=user_id,
                message_id=message_id,
                upload_id=existing_upload.id,
                file_sha256=file_sha256,
                size_bytes=size_bytes,
            )
            upload_dto = existing_upload
        else:
            # Create new upload record
            upload_dto = await self.upload_repo.create(
                {
                    "original_filename": file.filename,
                    "extension": extension,
                    "mime_type": mime_type,
                    "size_bytes": size_bytes,
                    "hash_id": hash_id,
                    "storage_backend": "local",  # TODO: make configurable
                    "storage_path": f"{hash_id}/{file.filename}",
                    "file_sha256": file_sha256,
                    "thumbnails_ready": False,
                }
            )

        # Step 6: Save file to temp directory
        os.makedirs(TEMP_DIR, exist_ok=True)
        temp_path = os.path.join(TEMP_DIR, f"{hash_id}_{file.filename}")

        with open(temp_path, "wb") as f:
            f.write(file_content)

        # Step 7: Create attachment record
        attachment_dto = await self.attachment_repo.create(
            {
                "message_id": message_id,
                "upload_id": upload_dto.id,
                "filename": file.filename,
            }
        )

        # Step 8: Emit event for async worker
        await self.event_protocol.emit(
            "attachment.uploaded",
            {
                "upload_id": upload_dto.id,
                "attachment_id": attachment_dto.id,
                "temp_path": temp_path,
                "original_filename": file.filename,
                "hash_id": hash_id,
                "extension": extension,
            },
        )

        # Step 9: Cache result (idempotency)
        if idempotency_key:
            await self.cache_manager.set(
                f"upload_idempotent:{idempotency_key}",
                attachment_dto.id,
                ttl=3600,
            )

        # Step 10: Log upload
        logger.info(
            "attachment.uploaded",
            attachment_id=attachment_dto.id,
            upload_id=upload_dto.id,
            user_id=user_id,
            message_id=message_id,
            size_bytes=size_bytes,
            extension=extension,
            hash_id=hash_id,
            content_type=mime_type,
            idempotency_key=idempotency_key,
        )

        return {
            "upload_id": str(attachment_dto.id),
            "status": "pending",
            "message": "File queued for processing",
        }

    async def download_attachment(self, attachment_id: str, user_id: int) -> dict:
        """
        Get presigned/download URL for attachment.
        User must have access to the message.
        """
        # Step 1: Get attachment from cache
        cache_key = f"attachment:{attachment_id}"
        attachment_dto = await self.cache_manager.get(cache_key)
        if not attachment_dto:
            attachment_dto = await self.attachment_repo.get_by_id(int(attachment_id))
            if attachment_dto:
                await self.cache_manager.set(cache_key, attachment_dto, ttl=3600)

        if not attachment_dto:
            logger.warning(
                "attachment.download_denied",
                attachment_id=attachment_id,
                user_id=user_id,
                reason="not_found",
            )
            raise NotFoundError(f"Attachment {attachment_id} not found")

        # Step 2: Get associated message
        message_dto = await self.message_repo.get_by_id(attachment_dto.message_id)
        if not message_dto:
            logger.warning(
                "attachment.download_denied",
                attachment_id=attachment_id,
                user_id=user_id,
                message_id=attachment_dto.message_id,
                reason="message_not_found",
            )
            raise NotFoundError("Associated message not found")

        # Step 3: Verify user permission
        is_allowed = await self._verify_message_permission(message_dto, user_id)
        if not is_allowed:
            logger.warning(
                "attachment.download_denied",
                attachment_id=attachment_id,
                user_id=user_id,
                message_id=attachment_dto.message_id,
                reason="user_not_authorized",
            )
            raise ForbiddenError("You do not have access to this attachment")

        # Step 4: Get upload metadata
        upload_dto = await self.upload_repo.get_by_id(attachment_dto.upload_id)
        if not upload_dto:
            logger.error(
                "attachment.download_failed",
                attachment_id=attachment_id,
                user_id=user_id,
                upload_id=attachment_dto.upload_id,
                error_code="internal_error",
                reason="upload_not_found",
            )
            raise NotFoundError("Upload record not found")

        # Step 5: Generate download URL
        url = await self.storage_client.generate_presigned_url(
            upload_dto.storage_path, expiration=3600
        )

        # Step 6: Log access
        logger.info(
            "attachment.downloaded",
            attachment_id=attachment_id,
            user_id=user_id,
            message_id=attachment_dto.message_id,
            filename=attachment_dto.filename,
            size_bytes=upload_dto.size_bytes,
        )

        return {"url": url}

    async def get_attachment_details(self, attachment_id: str, user_id: int) -> dict:
        """
        Get attachment metadata including thumbnails.
        """
        # Step 1: Get attachment from cache
        cache_key = f"attachment:{attachment_id}"
        attachment_dto = await self.cache_manager.get(cache_key)
        if not attachment_dto:
            attachment_dto = await self.attachment_repo.get_by_id(int(attachment_id))
            if attachment_dto:
                await self.cache_manager.set(cache_key, attachment_dto, ttl=3600)

        if not attachment_dto:
            raise NotFoundError(f"Attachment {attachment_id} not found")

        # Step 2: Get message for permission check
        message_dto = await self.message_repo.get_by_id(attachment_dto.message_id)
        if not message_dto:
            raise NotFoundError("Associated message not found")

        # Step 3: Verify user permission
        is_allowed = await self._verify_message_permission(message_dto, user_id)
        if not is_allowed:
            logger.warning(
                "attachment.metadata_denied",
                attachment_id=attachment_id,
                user_id=user_id,
                reason="user_not_authorized",
            )
            raise ForbiddenError("You do not have access to this attachment")

        # Step 4: Get upload details
        upload_dto = await self.upload_repo.get_by_id(attachment_dto.upload_id)
        if not upload_dto:
            raise NotFoundError("Upload record not found")

        # Step 5: Build thumbnail URLs
        thumbnails = {}
        if upload_dto.thumbnails_ready:
            for size in [128, 512, 1024]:
                url = await self.storage_client.generate_presigned_url(
                    f"{upload_dto.storage_path}/thumbnails/{size}", expiration=7200
                )
                thumbnails[size] = url

        # Step 6: Generate download URL
        download_url = await self.storage_client.generate_presigned_url(
            upload_dto.storage_path, expiration=3600
        )

        # Step 7: Log access
        logger.info(
            "attachment.metadata_fetched",
            attachment_id=attachment_id,
            user_id=user_id,
            filename=attachment_dto.filename,
            thumbnails_ready=upload_dto.thumbnails_ready,
        )

        return {
            "id": attachment_dto.id,
            "filename": attachment_dto.filename,
            "content_type": upload_dto.mime_type,
            "size_bytes": upload_dto.size_bytes,
            "download_url": download_url,
            "thumbnails": thumbnails,
        }

    async def get_thumbnail(
        self, attachment_id: str, size: int, user_id: int
    ) -> dict:
        """
        Get thumbnail URL. Returns 412 if thumbnails not ready.
        """
        # Step 1: Validate size
        if size not in [128, 512, 1024]:
            logger.warning(
                "attachment.thumbnail_invalid_size",
                attachment_id=attachment_id,
                user_id=user_id,
                size=size,
            )
            raise HTTPException(status_code=400, detail="Invalid thumbnail size")

        # Step 2: Check thumbnail cache
        cache_key = f"thumbnail:{attachment_id}:{size}"
        url = await self.cache_manager.get(cache_key)
        if url:
            logger.info(
                "attachment.thumbnail_cache_hit",
                attachment_id=attachment_id,
                user_id=user_id,
                size=size,
            )
            return {"size": size, "download_url": url}

        # Step 3: Get attachment metadata
        attachment_dto = await self.attachment_repo.get_by_id(int(attachment_id))
        if not attachment_dto:
            raise NotFoundError(f"Attachment {attachment_id} not found")

        # Step 4: Get message for permission check
        message_dto = await self.message_repo.get_by_id(attachment_dto.message_id)
        if not message_dto:
            raise NotFoundError("Associated message not found")

        # Step 5: Verify user permission
        is_allowed = await self._verify_message_permission(message_dto, user_id)
        if not is_allowed:
            logger.warning(
                "attachment.thumbnail_access_denied",
                attachment_id=attachment_id,
                user_id=user_id,
                reason="user_not_authorized",
            )
            raise ForbiddenError("You do not have access to this attachment")

        # Step 6: Get upload details
        upload_dto = await self.upload_repo.get_by_id(attachment_dto.upload_id)
        if not upload_dto:
            raise NotFoundError("Upload record not found")

        # Step 7: Check if thumbnails are ready
        if not upload_dto.thumbnails_ready:
            logger.info(
                "attachment.thumbnail_not_ready",
                attachment_id=attachment_id,
                user_id=user_id,
                size=size,
                status="processing",
            )
            raise HTTPException(
                status_code=412,
                detail="Thumbnail generation in progress. Try again later.",
            )

        # Step 8: Generate thumbnail URL
        url = await self.storage_client.generate_presigned_url(
            f"{upload_dto.storage_path}/thumbnails/{size}", expiration=7200
        )

        # Step 9: Cache thumbnail URL
        await self.cache_manager.set(cache_key, url, ttl=7200)

        # Step 10: Log access
        logger.info(
            "attachment.thumbnail_fetched",
            attachment_id=attachment_id,
            user_id=user_id,
            size=size,
            thumbnail_ready=True,
        )

        return {"size": size, "download_url": url}

    async def _verify_message_permission(self, message_dto, user_id: int) -> bool:
        """
        Verify user has permission to access message attachment.
        TODO: Implement actual room membership check.
        """
        logger.debug(
            "attachment.permission_check",
            user_id=user_id,
            message_id=message_dto.id,
            room_id=message_dto.room_id,
        )

        # TODO: Check if user is member of room
        # For now, assume True (placeholder)
        is_member = True

        # Use message policy to verify
        from app.domain.models.message_domain import MessageDomain

        message_domain = MessageDomain(
            id=message_dto.id,
            content=message_dto.content,
            sender_id=message_dto.sender_id,
            room_id=message_dto.room_id,
            created_at=message_dto.created_at,
            updated_at=message_dto.updated_at,
            attachments=[],
        )

        result = self.message_policy.can_access(message_domain, user_id, is_member)
        logger.debug(
            "attachment.permission_check_result",
            user_id=user_id,
            message_id=message_dto.id,
            result="allowed" if result else "denied",
        )

        return result

    async def get_attachments(self, message_id: int) -> List[AttachmentDomain]:
        """Get all attachments for a message."""
        dtos = await self.attachment_repo.get_by_message_id(message_id)
        return [
            AttachmentDomain(
                id=dto.id,
                message_id=dto.message_id,
                upload_id=dto.upload_id,
                filename=dto.filename,
                created_at=dto.created_at,
                updated_at=dto.updated_at,
            )
            for dto in dtos
        ]
