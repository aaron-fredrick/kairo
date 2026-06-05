from fastapi import Request
import uuid
import structlog

async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")
    
    if not request_id:
        request_id = str(uuid.uuid4())
        
    request.state.request_id = request_id
    
    structlog.contextvars.bind_contextvars(request_id=request_id)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id
    return response