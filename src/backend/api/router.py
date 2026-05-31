from fastapi import APIRouter
from src.backend.api.admin import router as admin_router
from src.backend.api.rooms import router as rooms_router
from src.backend.api.users import router as users_router
from src.backend.api.dm import router as dm_router
from src.backend.api.data import router as data_router

api_router = APIRouter(prefix="/api")
api_router.include_router(admin_router)
api_router.include_router(rooms_router)
api_router.include_router(users_router)
api_router.include_router(dm_router)
api_router.include_router(data_router)
