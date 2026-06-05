from fastapi import APIRouter
from .routers import *

# Master API Router
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(presence_router)
api_router.include_router(attachments_router)
api_router.include_router(messages_router)
api_router.include_router(rooms_router)
