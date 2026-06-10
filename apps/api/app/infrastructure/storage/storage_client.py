import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import structlog
from tenacity import retry, wait_fixed, stop_after_attempt, before_sleep_log
import logging
import os

logger = structlog.get_logger(__name__)
std_logger = logging.getLogger(__name__)

def get_boto_client():
    if settings.STORAGE_BACKEND in ("s3", "minio"):
        return boto3.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION
        )
    return None

boto_client = get_boto_client()

@retry(
    wait=wait_fixed(2),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(std_logger, logging.WARNING),
    reraise=True
)
async def check_storage_connection():
    """Verify storage connection with retries on startup"""
    if settings.STORAGE_BACKEND == "local":
        os.makedirs(os.path.join("data", "temp"), exist_ok=True)
        os.makedirs(os.path.join("data", "blobs"), exist_ok=True)
        logger.info("Local storage directories verified.")
        return

    try:
        # Run synchronous boto3 call in a simple way
        # In a real app we might use aioboto3, but boto3 is fine for simple ping
        boto_client.head_bucket(Bucket=settings.S3_BUCKET)
        logger.info(f"Successfully connected to S3/Minio bucket {settings.S3_BUCKET}.")
    except ClientError as e:
        # If bucket doesn't exist, we might try to create it, but for pinging, it's an error.
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            logger.warning(f"Bucket {settings.S3_BUCKET} does not exist. Attempting to create it.")
            try:
                if settings.S3_REGION == "us-east-1":
                    boto_client.create_bucket(Bucket=settings.S3_BUCKET)
                else:
                    boto_client.create_bucket(
                        Bucket=settings.S3_BUCKET,
                        CreateBucketConfiguration={'LocationConstraint': settings.S3_REGION}
                    )
                logger.info(f"Created bucket {settings.S3_BUCKET}.")
            except Exception as create_e:
                logger.error(f"Failed to create bucket: {create_e}")
                raise
        elif error_code == 403:
             logger.error("Access denied to storage bucket. Check credentials.")
             raise
        else:
             raise
    except Exception as e:
        logger.error(f"Storage connection failed: {e}")
        raise


class StorageClient:
    """Abstraction for storage operations (S3, MinIO, Local)."""
    
    def __init__(self, backend: str = "local"):
        self.backend = backend or settings.STORAGE_BACKEND
        self.bucket = settings.S3_BUCKET
    
    async def generate_presigned_url(self, object_name: str, expiration: int = 3600) -> str:
        """Generate presigned URL for object."""
        if self.backend in ("s3", "minio"):
            if not boto_client:
                raise RuntimeError("S3 client not initialized")
            
            try:
                response = boto_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': object_name},
                    ExpiresIn=expiration
                )
                logger.debug("storage.presigned_url_generated", object_name=object_name, backend=self.backend)
                return response
            except ClientError as e:
                logger.error(
                    "storage.presigned_url_failed",
                    object_name=object_name,
                    error=str(e)
                )
                raise
        else:
            # Local backend returns relative URL
            return f"/local-download/{object_name}"
    
    async def upload_to_temp(self, file_content: bytes, hash_id: str, filename: str) -> str:
        """Upload file to temporary directory."""
        temp_dir = "data/temp"
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_path = os.path.join(temp_dir, f"{hash_id}_{filename}")
        
        with open(temp_path, "wb") as f:
            f.write(file_content)
        
        logger.debug(
            "storage.file_uploaded_to_temp",
            temp_path=temp_path,
            size_bytes=len(file_content)
        )
        return temp_path
    
    async def move_file_from_temp(self, temp_path: str, target_path: str) -> bool:
        """Move file from temp to permanent storage."""
        if self.backend == "local":
            blobs_dir = "data/blobs"
            os.makedirs(blobs_dir, exist_ok=True)
            
            full_target = os.path.join(blobs_dir, target_path)
            os.makedirs(os.path.dirname(full_target), exist_ok=True)
            
            try:
                os.rename(temp_path, full_target)
                logger.info(
                    "storage.file_moved_to_permanent",
                    temp_path=temp_path,
                    target_path=full_target
                )
                return True
            except Exception as e:
                logger.error(
                    "storage.file_move_failed",
                    temp_path=temp_path,
                    target_path=full_target,
                    error=str(e)
                )
                return False
        else:
            # TODO: Implement S3/MinIO move
            logger.warning("storage.move_not_implemented_for_backend", backend=self.backend)
            return False


def get_storage_client() -> StorageClient:
    """Dependency injection for StorageClient."""
    return StorageClient()
