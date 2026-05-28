from fastapi import APIRouter
from app.files.upload import router as upload_router
from app.files.download import router as download_router
from app.files.thumbnail import router as thumbnail_router
from app.files.pfp import router as pfp_router

router = APIRouter()
router.include_router(upload_router, prefix="/upload", tags=["files"])
router.include_router(download_router, prefix="/download", tags=["files"])
router.include_router(thumbnail_router, prefix="/thumbnails", tags=["files"])
router.include_router(pfp_router, tags=["files", "users"])
