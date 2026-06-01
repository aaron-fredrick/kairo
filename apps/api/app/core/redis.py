import redis.asyncio as redis
from app.core.config import settings
import structlog
from tenacity import retry, wait_fixed, stop_after_attempt, before_sleep_log
import logging

logger = structlog.get_logger(__name__)
std_logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

@retry(
    wait=wait_fixed(2),
    stop=stop_after_attempt(5),
    before_sleep=before_sleep_log(std_logger, logging.WARNING),
    reraise=True
)
async def check_redis_connection():
    """Verify Redis connection with retries on startup"""
    try:
        await redis_client.ping()
        logger.info("Successfully connected to Redis.")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise

async def get_redis():
    return redis_client
