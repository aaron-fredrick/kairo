from fastapi import WebSocketException
from app.core.security import decode_access_token
import structlog

logger = structlog.get_logger(__name__)


async def get_ws_user_id(token: str) -> int:
    """
    Extract user_id from JWT token.
    Token is passed in query param on WebSocket connection.
    """
    if not token:
        logger.warning("ws.no_token_provided")
        raise WebSocketException(code=4001, reason="No token provided")

    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))

        logger.debug(
            "ws.token_decoded",
            user_id=user_id,
            token_type=payload.get("type"),
        )

        return user_id
    except Exception as e:
        logger.warning(
            "ws.token_decode_failed",
            error=str(e),
        )
        raise WebSocketException(code=4001, reason="Invalid token")
