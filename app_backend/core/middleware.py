from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app_backend.core.config import settings
from app_backend.core.logging import get_logger

logger = get_logger(__name__)


class IPAccessMiddleware(BaseHTTPMiddleware):
    """Block or allow requests based on configurable IP blacklist / whitelist."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip: str | None = request.client.host if request.client else None

        if client_ip:
            if settings.blacklist_ips and client_ip in settings.blacklist_ips:
                logger.warning("Blocked blacklisted IP: %s -> %s", client_ip, request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied: IP is blacklisted."},
                )

            if settings.whitelist_ips and client_ip not in settings.whitelist_ips:
                logger.warning("Blocked non-whitelisted IP: %s -> %s", client_ip, request.url.path)
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied: IP is not whitelisted."},
                )

            logger.debug("IP allowed: %s -> %s", client_ip, request.url.path)

        return await call_next(request)
