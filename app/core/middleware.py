from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

class IPAccessMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        if client_ip:
            if settings.blacklist_ips and client_ip in settings.blacklist_ips:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied: IP is blacklisted."}
                )
            
            if settings.whitelist_ips and client_ip not in settings.whitelist_ips:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Access denied: IP is not whitelisted."}
                )
                
        response = await call_next(request)
        return response
