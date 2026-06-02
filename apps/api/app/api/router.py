from fastapi import APIRouter
from app.api.routes.presence import router as presence_router
from app.api.routes.attachments import router as attachments_router
from app.api.routes.messages import router as messages_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.auth import router as auth_router

# Master API Router
api_router = APIRouter(prefix="/api")

api_router.include_router(auth_router)
api_router.include_router(presence_router)
api_router.include_router(attachments_router)
api_router.include_router(messages_router)
api_router.include_router(rooms_router)
