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

def generate_presigned_url(object_name, expiration=3600):
    if not boto_client:
        return f"/local-download/{object_name}"
    try:
        response = boto_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': settings.S3_BUCKET,
                                                            'Key': object_name},
                                                    ExpiresIn=expiration)
    except ClientError as e:
        logger.error(f"Error generating presigned url: {e}")
        return None
    return response
