# Attachment System - Abstraction Analysis

## Overview

The attachment system manages file uploads and downloads within messages. It follows a clean 8-layer architecture that separates HTTP routing, dependency injection, business logic, data access, storage operations, permissions checking, and domain modeling.

### Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 1: API Router & Endpoints                                     │
│  (/api/routers/attachments_router.py)                                │
│  POST   /attachments/upload/{message_id}                             │
│  GET    /attachments/download/{attachment_id}                        │
│  GET    /attachments/{attachment_id}/thumbnail/{size}                │
│  GET    /attachments/{attachment_id}                                 │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ Depends(get_current_user_id)
                             │ Depends(get_upload_service)
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 2: Dependency Injection & Services                            │
│  (api/dependencies/services.py)                                      │
│  - get_upload_service() -> AttachmentService instance                │
│  - Service requires: AttachmentRepo, MessageRepo, MessagePolicy,     │
│    StorageClient, EventProtocol, CacheManager                        │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ Depends(get_attachment_repo)
                             │ Depends(get_message_repo)
                             │ Depends(get_message_policy)
                             │ Depends(get_storage_client)
                             │ Depends(get_event_protocol)
                             │ Depends(get_cache_manager)
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 3: Application Service (Business Logic)                       │
│  (application/services/attachment_service.py)                        │
│  - upload_file(file, message_id, user_id, idempotency_key)           │
│  - download_attachment(attachment_id, user_id)                       │
│  - get_attachment_details(attachment_id, user_id)                    │
│  - get_thumbnail(attachment_id, size, user_id)                       │
│  - verify_message_permission(message_id, user_id)                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ↓                   ↓                   ↓
┌─────────────────┐ ┌──────────────────┐ ┌─────────────────┐
│ Layer 4: Repo   │ │ Layer 5: Policy  │ │ Layer 6: Cache  │
│ (Data Access)   │ │ (Authorization)  │ │                 │
│                 │ │                  │ │ - Check msg     │
│ - Attachment    │ │ MessagePolicy    │ │ - Check perms   │
│   Repository    │ │ .can_access()    │ │ - Cache blobs   │
│                 │ │                  │ │                 │
│ - Message       │ │ Logic: is_member │ │ CacheManager    │
│   Repository    │ │ && message in    │ │                 │
│                 │ │ room             │ │ (Local + Redis) │
│ - Upload        │ │                  │ │                 │
│   Repository    │ │ Note: Room       │ │                 │
│                 │ │ membership check │ │                 │
│ QueryBases:     │ │ not yet          │ │                 │
│ - get_by_id()   │ │ implemented      │ │                 │
│ - get_by_msg_id │ │                  │ │                 │
│ - save()        │ │                  │ │                 │
└────────┬────────┘ └──────────────────┘ └─────────────────┘
         │
         ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 7: Database & ORM                                             │
│  (infrastructure/db/orm/)                                            │
│                                                                       │
│  MessageORM ──┐                                                      │
│     ├─ id                                                            │
│     ├─ content                                                       │
│     ├─ sender_id (FK)                                               │
│     ├─ room_id (FK)                                                 │
│     └─ attachments ──→ [AttachmentORM]                              │
│                                                                       │
│  AttachmentORM                                                       │
│     ├─ id                                                            │
│     ├─ message_id (FK)                                              │
│     ├─ upload_id (FK)                                               │
│     ├─ filename (user-provided name at time of attach)              │
│     ├─ created_at                                                   │
│     └─ updated_at                                                   │
│                                                                       │
│  UploadORM                                                           │
│     ├─ id                                                            │
│     ├─ original_filename (server-generated)                         │
│     ├─ extension                                                    │
│     ├─ mime_type                                                    │
│     ├─ size_bytes                                                   │
│     ├─ hash_id (unique ID for deduplication)                        │
│     ├─ storage_backend (s3/minio/local)                             │
│     ├─ storage_path (path in storage system)                        │
│     ├─ file_sha256 (content hash)                                   │
│     ├─ thumbnails_ready (bool)                                      │
│     ├─ thumbnail_sha256_sm                                          │
│     ├─ thumbnail_sha256_md                                          │
│     └─ thumbnail_sha256_lg                                          │
│                                                                       │
│  RoomORM (for permission checking)                                  │
│     ├─ id                                                            │
│     ├─ name                                                         │
│     ├─ description                                                  │
│     └─ messages ──→ [MessageORM]                                    │
└────────────────────────────┬─────────────────────────────────────────┘
                             │
                             ↓
┌──────────────────────────────────────────────────────────────────────┐
│  Layer 8: Storage Layer                                              │
│  (infrastructure/storage/storage_client.py)                          │
│                                                                       │
│  Supports: S3, MinIO, Local File System                              │
│  - Upload file to temp directory                                    │
│  - Stream file from storage                                         │
│  - Generate presigned URLs (S3/MinIO)                               │
│  - Generate local URLs (local backend)                              │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Layer Breakdown

### Layer 1: API Router & Endpoints

**File:** `app/api/routers/attachments_router.py`

**Endpoints:**

```python
POST /attachments/upload/{message_id}
├─ Headers: Idempotency-Key (optional)
├─ Body: UploadFile
├─ Auth: get_current_user_id
└─ Response: UploadResponseSchema
   └─ { upload_id, status, message }

GET /attachments/download/{attachment_id}
├─ Auth: get_current_user_id
└─ Response: DownloadUrlResponseSchema
   └─ { url }

GET /attachments/{attachment_id}
├─ Auth: get_current_user_id
└─ Response: AttachmentResponseSchema
   └─ { id, filename, content_type, size_bytes, download_url, thumbnails }

GET /attachments/{attachment_id}/thumbnail/{size}
├─ Path Param: size (128, 512, 1024)
├─ Auth: get_current_user_id
└─ Response: ThumbnailResponseSchema
   └─ { size, download_url }
```

**Current State:** Router is scaffolded with stubs; endpoints have no implementation.

---

### Layer 2: Dependency Injection & Composition

**File:** `app/api/dependencies/services.py` (new entry) + `container.py`

**Service Factory:**

```python
async def get_upload_service() -> AttachmentService:
    container = Depends(get_container)  # Singleton AppContainer
    
    attachment_repo = AttachmentRepository(db_session)
    message_repo = MessageRepository(db_session)
    message_policy = MessagePolicy()
    storage_client = get_storage_client()
    event_manager = get_event_manager()
    cache_manager = container.cache_manager
    
    return AttachmentService(
        attachment_repo,
        message_repo,
        message_policy,
        storage_client,
        event_manager,
        cache_manager
    )
```

**Composition Flow:**
- Router depends on `get_current_user_id` (JWT extraction)
- Router depends on `get_upload_service` (service instantiation)
- Service constructor receives:
  - `AttachmentRepository`: Data access for attachments
  - `MessageRepository`: Data access for messages
  - `MessagePolicy`: Authorization logic
  - `StorageClient`: File system integration
  - `EventProtocol`: Event emission (async worker pickup)
  - `CacheManager`: Session caching for permission verification

---

### Layer 3: Application Service

**File:** `app/application/services/attachment_service.py`

**Core Methods:**

#### 1. `upload_file(file: UploadFile, message_id: int, user_id: int, idempotency_key: Optional[str])`

**Flow:**
```
1. Verify message exists
   └─ message_dto = await message_repo.get_by_id(message_id)
   └─ Raise NotFoundError if missing

2. Verify user is message author
   └─ if message_dto.sender_id != user_id:
      └─ Raise ForbiddenError("Only message author can add attachments")
   
3. Idempotency check (if idempotency_key provided)
   └─ cache_manager.get(f"upload_idempotent:{idempotency_key}")
   └─ Return cached result if exists

4. Compute file hash & metadata
   └─ file_sha256 = compute_sha256(file.file)
   └─ Rewind file pointer to start
   └─ mime_type = file.content_type
   └─ original_filename = generate_hash_based_name(file.filename, hash_id)
   └─ extension = extract_extension(file.filename)
   └─ size_bytes = file.size

5. Check for duplicate (content-addressed storage)
   └─ existing_upload = await upload_repo.get_by_hash(file_sha256)
   └─ If exists: reuse upload record
   └─ Else: create new upload record in DB

6. Save file to storage
   └─ temp_path = f"data/temp/{hash_id}_{original_filename}"
   └─ stream_to_disk(file.file, temp_path)  # Async upload to temp
   └─ Emit event: { "type": "attachment.uploaded", "upload_id": upload.id, 
                      "temp_path": temp_path, "original_filename": ... }
   └─ Worker subscribes: moves temp → blob storage, generates thumbnails

7. Create attachment record
   └─ attachment_dto = AttachmentDTO(message_id, upload_id, filename)
   └─ attachment = await attachment_repo.save(attachment_dto)

8. Cache result (idempotency)
   └─ cache_manager.set(f"upload_idempotent:{idempotency_key}", upload_id, ttl=3600)

9. Log upload
   └─ logger.info("attachment.uploaded", attachment_id=attachment.id, 
                   user_id=user_id, message_id=message_id, size_bytes=size_bytes,
                   hash_id=hash_id)

10. Return UploadResponseSchema
   └─ { upload_id: str(attachment.id), status: "pending", 
        message: "File queued for processing" }
```

**Logging Detail:**
- `level: INFO`, `event: attachment.uploaded`
- `attachment_id, user_id, message_id, size_bytes, extension, hash_id, idempotency_key`
- On error: `level: ERROR`, `event: attachment.upload_failed`, `error_code, reason`

**Permissions:** Message author only (sender_id == user_id)

---

#### 2. `download_attachment(attachment_id: str, user_id: int)`

**Flow:**
```
1. Get attachment metadata from cache
   └─ cache_key = f"attachment:{attachment_id}"
   └─ attachment_dto = cache_manager.get(cache_key)
   └─ If cache miss:
      └─ attachment_dto = await attachment_repo.get_by_id(attachment_id)
      └─ cache_manager.set(cache_key, attachment_dto, ttl=3600)
   └─ Raise NotFoundError if missing

2. Get associated message
   └─ message_dto = await message_repo.get_by_id(attachment_dto.message_id)
   └─ Raise NotFoundError if missing

3. Verify user permission to access message
   └─ is_member = await verify_message_permission(message_dto, user_id)
   └─ Raise ForbiddenError if not permitted

4. Get upload metadata
   └─ upload_dto = await upload_repo.get_by_id(attachment_dto.upload_id)
   └─ Raise NotFoundError if missing

5. Generate download URL
   └─ If storage_backend == "s3" or "minio":
      └─ url = generate_presigned_url(upload_dto.storage_path, expiration=3600)
   └─ Else (local):
      └─ url = f"/local-download/{upload_dto.storage_path}"

6. Log access
   └─ logger.info("attachment.downloaded", attachment_id=attachment_id, 
                   user_id=user_id, size_bytes=upload_dto.size_bytes)

7. Return DownloadUrlResponseSchema
   └─ { url: download_url }
```

**Logging Detail:**
- `level: INFO`, `event: attachment.downloaded`
- `attachment_id, user_id, message_id, filename, size_bytes`
- On error: `level: WARNING`, `event: attachment.download_denied`, `reason: forbidden|not_found`

**Permissions:** User must have access to the message (message.room_id check pending)

---

#### 3. `get_attachment_details(attachment_id: str, user_id: int)`

**Flow:**
```
1. Get attachment from cache
   └─ cache_key = f"attachment:{attachment_id}"
   └─ attachment_dto = cache_manager.get(cache_key)
   └─ If cache miss:
      └─ attachment_dto = await attachment_repo.get_by_id(attachment_id)

2. Get message for permission check
   └─ message_dto = await message_repo.get_by_id(attachment_dto.message_id)
   └─ Raise NotFoundError if missing

3. Verify user permission
   └─ is_member = await verify_message_permission(message_dto, user_id)
   └─ Raise ForbiddenError if not permitted

4. Get upload details
   └─ upload_dto = await upload_repo.get_by_id(attachment_dto.upload_id)

5. Build response
   └─ thumbnails = {}
   └─ If upload.thumbnails_ready:
      └─ For each size in [128, 512, 1024]:
         └─ url = generate_thumbnail_url(upload.id, size)
         └─ thumbnails[size] = url

6. Log access
   └─ logger.info("attachment.metadata_fetched", attachment_id=attachment_id,
                   user_id=user_id)

7. Return AttachmentResponseSchema
   └─ { id: attachment.id, 
        filename: attachment.filename, 
        content_type: upload.mime_type,
        size_bytes: upload.size_bytes,
        download_url: presigned_url,
        thumbnails: { 128: url, 512: url, 1024: url } }
```

**Logging Detail:**
- `level: INFO`, `event: attachment.metadata_fetched`
- `attachment_id, user_id, filename, thumbnails_ready`
- On error: `level: WARNING`, `event: attachment.metadata_denied`, `reason`

**Permissions:** Same as download (user must access message)

---

#### 4. `get_thumbnail(attachment_id: str, size: ThumbnailSize, user_id: int)`

**Flow:**
```
1. Validate size
   └─ if size not in [128, 512, 1024]:
      └─ Raise ValueError("Invalid thumbnail size")

2. Check thumbnail cache
   └─ cache_key = f"thumbnail:{attachment_id}:{size}"
   └─ url = cache_manager.get(cache_key)
   └─ If cache hit: jump to step 9

3. Get attachment metadata
   └─ attachment_dto = await attachment_repo.get_by_id(attachment_id)
   └─ Raise NotFoundError if missing

4. Get message for permission check
   └─ message_dto = await message_repo.get_by_id(attachment_dto.message_id)

5. Verify user permission
   └─ is_member = await verify_message_permission(message_dto, user_id)
   └─ Raise ForbiddenError if not permitted

6. Get upload details
   └─ upload_dto = await upload_repo.get_by_id(attachment_dto.upload_id)
   └─ Raise HTTPException(412) if not upload.thumbnails_ready

7. Generate thumbnail URL
   └─ If storage_backend == "s3" or "minio":
      └─ url = generate_presigned_url(
           f"{upload_dto.storage_path}/thumbnails/{size}", 
           expiration=3600
         )
   └─ Else:
      └─ url = f"/local-download/{upload_dto.storage_path}/thumbnails/{size}"

8. Cache thumbnail URL
   └─ cache_manager.set(cache_key, url, ttl=7200)

9. Log access
   └─ logger.info("attachment.thumbnail_fetched", attachment_id=attachment_id,
                   user_id=user_id, size=size, thumbnail_ready=True)

10. Return ThumbnailResponseSchema
    └─ { size: size, download_url: url }
```

**Logging Detail:**
- `level: INFO`, `event: attachment.thumbnail_fetched`
- `attachment_id, user_id, size`
- On error: `level: WARNING`, `event: attachment.thumbnail_access_denied`, `reason`
- On not ready: `level: INFO`, `event: attachment.thumbnail_not_ready`, `status: processing`

**Permissions:** Same as download

**Note:** Return 412 Precondition Failed if thumbnails not yet ready (worker still processing)

---

#### 5. `verify_message_permission(message_dto: MessageDTO, user_id: int) -> bool`

**Flow:**
```
1. Check if message belongs to a room
   └─ if not message_dto.room_id:
      └─ return False  # Direct messages not yet supported

2. TODO: Check if user is member of room
   └─ is_member = await check_room_membership(message_dto.room_id, user_id)
   └─ return is_member
   
   # Current placeholder: assume True (will be implemented)
   └─ is_member = True

3. Use message policy to verify
   └─ message_domain = convert_dto_to_domain(message_dto)
   └─ return message_policy.can_access(message_domain, user_id, is_member)
```

**Logging Detail:**
- `level: DEBUG`, `event: attachment.permission_check`, `user_id, message_id, result: allowed|denied`

**Note:** Room membership check is pending implementation. For now, assumes all users have access.

---

### Layer 4: Repository Pattern (Data Access)

**Files:** 
- `infrastructure/repositories/attachment_repository.py`
- `infrastructure/repositories/message_repository.py`
- `infrastructure/repositories/upload_repository.py` (new)

**AttachmentRepository Methods:**

```python
async def get_by_id(self, id: int) -> Optional[AttachmentDTO]
async def get_by_message_id(self, message_id: int) -> List[AttachmentDTO]
async def save(self, dto: AttachmentDTO) -> AttachmentDTO
async def delete(self, id: int) -> bool
```

**MessageRepository Methods:**

```python
async def get_by_id(self, id: int) -> Optional[MessageDTO]
async def get_by_room(self, room_id: int) -> List[MessageDTO]
```

**UploadRepository Methods (new):**

```python
async def get_by_id(self, id: int) -> Optional[UploadDTO]
async def get_by_hash(self, file_sha256: str) -> Optional[UploadDTO]
async def save(self, dto: UploadDTO) -> UploadDTO
async def update_thumbnails_ready(self, id: int, ready: bool, hashes: dict) -> UploadDTO
```

**ORM → DTO Conversion:**
- All repositories extend `BaseRepository[ORM, DTO]`
- Enforces boundary: ORM never escapes repository
- All public methods return DTO or List[DTO]

---

### Layer 5: Authorization Policy

**File:** `domain/policies/message_policy.py`

**Current Implementation:**

```python
class MessagePolicy:
    """Authorization rules for attachment access via message."""
    
    def can_access(self, message: MessageDomain, user_id: int, is_member: bool) -> bool:
        return is_member and message.room_id is not None
```

**Usage in Service:**

```python
async def verify_message_permission(self, message_dto: MessageDTO, user_id: int) -> bool:
    is_member = await check_room_membership(message_dto.room_id, user_id)
    message_domain = MessageDomain(...)
    return self.message_policy.can_access(message_domain, user_id, is_member)
```

**Future Enhancement:** Implement `check_room_membership()` to verify user is in room.

---

### Layer 6: Cache Layer

**File:** `infrastructure/cache/cache_manager.py`

**Cached Keys:**

```
attachment:{attachment_id}
    Value: AttachmentDTO (serialized)
    TTL: 3600 seconds (1 hour)
    Invalidation: On attachment update/delete

thumbnail:{attachment_id}:{size}
    Value: { size, download_url }
    TTL: 7200 seconds (2 hours)
    Invalidation: Manual or on TTL expiry

upload_idempotent:{idempotency_key}
    Value: upload_id (or full UploadResponseSchema)
    TTL: 3600 seconds (1 hour)
    Purpose: Prevent duplicate uploads
```

**Strategy:** Hybrid (Local LRU + Redis)
- **Local TTL:** 50% of declared TTL (conservative — local cache is not source of truth)
- **Redis TTL:** 100% of declared TTL
- **Fallback:** If local cache miss, check Redis; if Redis miss, query DB

---

### Layer 7: Database Schema

**Tables:**

#### attachments
```sql
CREATE TABLE attachments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    message_id INT NOT NULL FOREIGN KEY → messages.id (CASCADE),
    upload_id INT NOT NULL FOREIGN KEY → uploads.id (CASCADE),
    filename VARCHAR(255) NOT NULL,  -- User-provided name at attachment time
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (message_id),
    INDEX (upload_id)
);
```

#### uploads
```sql
CREATE TABLE uploads (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_filename VARCHAR(255) NOT NULL,
    extension VARCHAR(20) NOT NULL,
    mime_type VARCHAR(120) NOT NULL,
    size_bytes BIGINT NOT NULL,
    hash_id VARCHAR(64) NOT NULL UNIQUE,
    storage_backend VARCHAR(20) NOT NULL,  -- 's3' | 'minio' | 'local'
    storage_path TEXT NOT NULL,
    file_sha256 VARCHAR(64) NOT NULL,
    thumbnails_ready BOOLEAN DEFAULT FALSE,
    thumbnail_sha256_sm VARCHAR(64),
    thumbnail_sha256_md VARCHAR(64),
    thumbnail_sha256_lg VARCHAR(64),
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    INDEX (hash_id),
    INDEX (file_sha256)
);
```

**Relationships:**
- `messages.id` → `attachments.message_id` (1:N)
- `attachments.upload_id` → `uploads.id` (N:1, allows file deduplication)
- Cascade delete on message → attachment
- Cascade delete on upload → attachment (if no other messages reference it)

---

### Layer 8: Storage Layer

**File:** `infrastructure/storage/storage_client.py`

**Supported Backends:** S3, MinIO, Local Filesystem

**Operations:**

#### `upload_to_temp(file_content: bytes, hash_id: str, filename: str) -> str`
- Saves file to temporary directory
- Returns: temp_path for event emission
- Used by: AttachmentService.upload_file()

#### `generate_presigned_url(storage_path: str, expiration: int = 3600) -> str`
- Returns S3/MinIO presigned URL (or local URL if using local backend)
- Expiration: 3600 seconds (1 hour)
- Used by: download_attachment(), get_attachment_details(), get_thumbnail()

#### `move_file_from_temp(temp_path: str, target_path: str) -> bool`
- Called by async worker
- Moves file from temp to permanent blob storage
- Updates upload record with final storage_path

#### `generate_thumbnail(upload_id: int, size: ThumbnailSize) -> str`
- Called by async worker
- Generates thumbnails (128x128, 512x512, 1024x1024)
- Stores in `{storage_path}/thumbnails/{size}`

---

## Request Flow Examples

### Example 1: Upload File to Message

```
User Action:
  POST /attachments/upload/42
  Body: { file: <binary> }
  Headers: { Authorization: Bearer <token>, Idempotency-Key: abc123 }

FastAPI Flow:
  ├─ get_current_user_id(token) → user_id = 5
  ├─ get_upload_service() → AttachmentService instance
  │
Service Flow:
  ├─ Verify message 42 exists
  ├─ Verify user 5 is sender of message 42
  ├─ Check idempotency: cache.get("upload_idempotent:abc123") → miss
  ├─ Compute SHA256(file) → hash_id = "abc123def456"
  ├─ Check upload deduplication: upload_repo.get_by_hash() → miss (new file)
  ├─ Create upload record in DB
  │   └─ UploadORM(original_filename, extension, mime_type, size_bytes, 
  │       hash_id, storage_backend, storage_path, file_sha256)
  │
Storage Flow:
  ├─ Save to temp: "data/temp/abc123def456_photo.jpg"
  │
Event Flow:
  ├─ Emit: { type: "attachment.uploaded", upload_id: 17, 
             temp_path: "data/temp/abc123def456_photo.jpg", ... }
  │
Database Flow:
  ├─ Create attachment record:
  │   └─ AttachmentORM(message_id=42, upload_id=17, filename="photo.jpg")
  │
Cache Flow:
  ├─ Set cache: "upload_idempotent:abc123" → "17" (ttl=3600s)
  │
Response:
  └─ 200 OK: { upload_id: "17", status: "pending", 
              message: "File queued for processing" }

Async Worker (subscribes to attachment.uploaded):
  ├─ Receives event
  ├─ Move file: "data/temp/..." → "data/blobs/abc123def456/photo.jpg" (or S3)
  ├─ Generate thumbnails: sizes 128, 512, 1024
  ├─ Update upload record:
  │   └─ thumbnails_ready = TRUE
  │   └─ thumbnail_sha256_sm, thumbnail_sha256_md, thumbnail_sha256_lg
  │
Logging (Attach Service):
  └─ INFO: { event: "attachment.uploaded", attachment_id: 17, user_id: 5,
             message_id: 42, size_bytes: 245638, extension: "jpg",
             hash_id: "abc123def456", idempotency_key: "abc123" }
```

---

### Example 2: Download Attachment

```
User Action:
  GET /attachments/download/17
  Headers: { Authorization: Bearer <token> }

FastAPI Flow:
  ├─ get_current_user_id(token) → user_id = 3
  ├─ get_upload_service() → AttachmentService instance

Service Flow:
  ├─ Cache check: "attachment:17" → miss
  ├─ Get attachment from DB: attachment_id=17, message_id=42, upload_id=17
  ├─ Cache update: set "attachment:17" (ttl=3600s)
  │
Permission Check:
  ├─ Get message: message_id=42, room_id=8, sender_id=5
  ├─ Verify permission: is_member(user_id=3, room_id=8) → ✓ allowed
  │   └─ Uses message_policy.can_access()
  │
Storage Flow:
  ├─ Get upload: upload_id=17, storage_path="blobs/abc123def456/photo.jpg"
  ├─ Generate presigned URL: 
  │   └─ S3: "https://s3.amazonaws.com/bucket/...?Signature=..."
  │   └─ Local: "/local-download/blobs/abc123def456/photo.jpg"
  │
Response:
  └─ 200 OK: { url: "https://s3.amazonaws.com/..." }

Logging:
  └─ INFO: { event: "attachment.downloaded", attachment_id: 17, user_id: 3,
             size_bytes: 245638, filename: "photo.jpg", message_id: 42 }
```

---

### Example 3: Get Thumbnail (Permission Denied)

```
User Action:
  GET /attachments/99/thumbnail/512
  Headers: { Authorization: Bearer <token> }

FastAPI Flow:
  ├─ get_current_user_id(token) → user_id = 99 (different user)
  ├─ get_upload_service() → AttachmentService instance

Service Flow:
  ├─ Cache check: "thumbnail:99:512" → miss
  ├─ Get attachment: attachment_id=99, message_id=50, upload_id=99
  ├─ Get message: message_id=50, room_id=2
  │
Permission Check:
  ├─ Verify permission: is_member(user_id=99, room_id=2) → ✗ denied
  │   └─ User is not in room 2
  ├─ message_policy.can_access() → false
  │
Error Response:
  └─ 403 Forbidden: { detail: "You do not have access to this attachment" }

Logging:
  └─ WARNING: { event: "attachment.thumbnail_access_denied", 
                attachment_id: 99, user_id: 99, size: 512,
                reason: "user_not_in_room" }
```

---

## Abstraction Patterns

### 1. **Repository Pattern**
- ORM never escapes the repository boundary
- Conversion to DTO enforced at repository exit
- Enables swapping storage implementation without affecting service layer

### 2. **Policy-Based Authorization**
- `MessagePolicy` encapsulates access logic
- Pure business logic — no DB, no HTTP dependencies
- Testable independently of service

### 3. **Dual-Layer Caching**
- Local in-memory (fast, not shared)
- Redis backend (slow, but shared across instances)
- Fallback: Local miss → Redis miss → DB query

### 4. **Content-Addressed Storage**
- File deduplicated by SHA256 hash
- Multiple `attachments` can point to same `upload` (if file reused)
- Saves storage space

### 5. **Presigned URL Pattern**
- Client receives short-lived download URL
- Backend doesn't stream file (reduces server load)
- Applicable to S3/MinIO; local backend returns fake presigned URL

### 6. **Event-Driven Async Processing**
- Upload endpoint returns immediately with `status: "pending"`
- Async worker processes (move file, generate thumbnails)
- Reduces request latency, improves perceived performance

### 7. **Idempotency Key Pattern**
- Upload endpoint accepts `Idempotency-Key` header
- Prevents duplicate uploads from retries
- Cached response ensures same result on retry

---

## Permission Model

### Access Rules

| Action | Rule | Status |
|--------|------|--------|
| **Upload** | User must be message author | ✓ Implemented |
| **Download** | User must be in message's room | ⚠ TODO: Room membership check |
| **Get Metadata** | User must be in message's room | ⚠ TODO: Room membership check |
| **Get Thumbnail** | User must be in message's room | ⚠ TODO: Room membership check |

### Room Membership Check (TODO)

Current placeholder in `verify_message_permission()`:
```python
is_member = True  # TODO: Implement room membership verification
```

Required implementation:
1. Query room_users table (when created) OR
2. Check presence service for active users OR
3. Use cache-based membership tracking

---

## Logging Strategy

### Upload Operation
```json
{
  "level": "INFO",
  "event": "attachment.uploaded",
  "attachment_id": 17,
  "user_id": 5,
  "message_id": 42,
  "size_bytes": 245638,
  "extension": "jpg",
  "hash_id": "abc123def456",
  "content_type": "image/jpeg",
  "idempotency_key": "abc123"
}
```

**On Error:**
```json
{
  "level": "ERROR",
  "event": "attachment.upload_failed",
  "user_id": 5,
  "message_id": 42,
  "error_code": "forbidden",
  "reason": "user_not_message_author"
}
```

### Download Operation
```json
{
  "level": "INFO",
  "event": "attachment.downloaded",
  "attachment_id": 17,
  "user_id": 3,
  "message_id": 42,
  "filename": "photo.jpg",
  "size_bytes": 245638
}
```

**On Permission Denied:**
```json
{
  "level": "WARNING",
  "event": "attachment.download_denied",
  "attachment_id": 17,
  "user_id": 3,
  "message_id": 42,
  "reason": "user_not_in_room"
}
```

### Permission Check (Debug)
```json
{
  "level": "DEBUG",
  "event": "attachment.permission_check",
  "user_id": 3,
  "message_id": 42,
  "room_id": 8,
  "result": "allowed"
}
```

### Thumbnail Processing
```json
{
  "level": "INFO",
  "event": "attachment.thumbnail_fetched",
  "attachment_id": 17,
  "user_id": 3,
  "size": 512,
  "thumbnail_ready": true
}
```

**If Not Ready:**
```json
{
  "level": "INFO",
  "event": "attachment.thumbnail_not_ready",
  "attachment_id": 17,
  "user_id": 3,
  "status": "processing",
  "http_response": 412
}
```

---

## Known Issues & Design Decisions

### Issue 1: Room Membership Not Implemented
- **Status:** Placeholder only
- **Impact:** Any authenticated user can download any attachment (security risk)
- **Solution:** Implement `check_room_membership()` query
- **Recommendation:** Use presence service or dedicated room_users table

### Issue 2: No Rate Limiting on Upload
- **Status:** Not implemented
- **Impact:** User can upload unlimited files, causing storage exhaustion
- **Solution:** Add rate limiting at router level (e.g., 5 files/hour per user)
- **Recommendation:** FastAPI-limiter middleware

### Issue 3: No Virus Scanning
- **Status:** Not implemented
- **Impact:** Malicious files could be uploaded
- **Solution:** Integrate with ClamAV or similar before moving from temp
- **Recommendation:** Async worker should scan before final storage

### Issue 4: Thumbnail Generation Not Asynchronous
- **Status:** Event emitted, but worker code not shown
- **Impact:** If worker fails silently, thumbnail never generated
- **Solution:** Add retry logic and dead-letter queue for failed thumbnail jobs
- **Recommendation:** Use job queue (Celery, RQ) with retries

### Issue 5: Storage Path Collision
- **Status:** Using hash_id to prevent collisions
- **Impact:** Low risk if hash algorithm is strong (SHA256)
- **Solution:** Include timestamp or UUID in path as secondary unique key
- **Recommendation:** `storage_path = f"{year}/{month}/{hash_id}/{original_filename}"`

### Issue 6: Presigned URL Expiration
- **Status:** Hard-coded 3600 seconds (1 hour)
- **Impact:** User might receive URL that expires before download completes
- **Solution:** Make expiration configurable per operation
- **Recommendation:** `expiration = config.PRESIGNED_URL_TTL (default 3600)`

---

## Design Decisions

### Why Content-Addressed Storage?
- **Benefit:** Deduplication reduces storage costs
- **Trade-off:** Extra SHA256 computation on upload
- **Rationale:** For a chat app with photos, file reuse is common (stickers, memes)

### Why Event-Driven Async Processing?
- **Benefit:** Fast response to user, background work doesn't block
- **Trade-off:** Thumbnail generation latency (user sees "processing" initially)
- **Rationale:** Thumbnail generation is CPU-intensive; don't block upload endpoint

### Why Hybrid Cache (Local + Redis)?
- **Benefit:** Fast local access, shared cache across instances
- **Trade-off:** Memory overhead, cache invalidation complexity
- **Rationale:** Attachments are frequently accessed (download, metadata checks)

### Why Idempotency Key?
- **Benefit:** Prevent duplicate uploads on network retry
- **Trade-off:** Cache entry per upload (minor memory cost)
- **Rationale:** Uploads can fail mid-stream; retry is common user behavior

### Why Presigned URLs Instead of Streaming?
- **Benefit:** Server doesn't stream data (lower CPU/bandwidth)
- **Trade-off:** Loss of download monitoring/control
- **Rationale:** For static files, presigned URL is standard and efficient

---

## Files to Know

### Core Service
- [attachment_service.py](attachment_service.py) — Business logic (upload, download, metadata, thumbnails)
- [attachments_router.py](attachments_router.py) — HTTP endpoints

### Data Access
- [attachment_repository.py](attachment_repository.py) — Attachment queries
- [message_repository.py](message_repository.py) — Message queries (for permission checks)
- [upload_repository.py](upload_repository.py) — Upload records (TODO: create)

### ORM Models
- [attachment_orm.py](attachment_orm.py) — SQLAlchemy Attachment model
- [upload_orm.py](upload_orm.py) — SQLAlchemy Upload model
- [message_orm.py](message_orm.py) — SQLAlchemy Message model (for relationships)

### Domain Models
- [attachment_domain.py](attachment_domain.py) — Attachment business entity
- [message_domain.py](message_domain.py) — Message business entity

### DTOs
- [attachment_dto.py](attachment_dto.py) — Data transfer object

### Schemas (Validation)
- [attachment_schema.py](attachment_schema.py) — Request/response validation

### Storage & Caching
- [storage_client.py](storage_client.py) — S3/MinIO/Local file operations
- [cache_manager.py](cache_manager.py) — Local + Redis hybrid cache

### Authorization
- [message_policy.py](message_policy.py) — Access control logic

### Logging
- All files use `structlog` for structured logging
- Log level and event type aid debugging

---

## Testing Strategy

### Unit Tests
- `AttachmentService.upload_file()` — Mock storage, repository
- `AttachmentService.download_attachment()` — Mock permission check, repository
- `MessagePolicy.can_access()` — Test access rules in isolation

### Integration Tests
- Full upload flow with temp storage
- Download with presigned URL generation
- Permission verification with message lookups

### E2E Tests
- POST /attachments/upload/{message_id} with file
- GET /attachments/download/{attachment_id}
- GET /attachments/{attachment_id}
- GET /attachments/{attachment_id}/thumbnail/{size}

---

## Summary

The attachment system uses a **clean 8-layer architecture** that separates concerns:

1. **Router** — HTTP interface
2. **Dependency Injection** — Service composition
3. **Application Service** — Business logic (upload, download, permissions)
4. **Repository** — Data access (ORM → DTO boundary)
5. **Authorization Policy** — Access control rules
6. **Cache** — Hybrid local + Redis
7. **Database** — ORM models and relationships
8. **Storage** — S3/MinIO/Local file operations

**Key Patterns:**
- Content-addressed storage (deduplication)
- Event-driven async processing (thumbnails)
- Dual-layer caching (performance)
- Idempotency keys (reliability)
- Presigned URLs (efficiency)
- Policy-based authorization (testability)

**Outstanding Work:**
- Room membership verification (needed for permission checks)
- Upload rate limiting
- Virus scanning integration
- Thumbnail retry logic
- Storage path collision mitigation

**Logging:** Comprehensive structured logs at each layer for easy debugging.
