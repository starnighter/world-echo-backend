from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.responses import success_response
from app.db.models import User
from app.schemas.upload import UploadResponse
from app.services.storage_service import StorageService


router = APIRouter()
settings = get_settings()
storage_service = StorageService(settings)


@router.post("/image")
async def upload_image(
    _: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    url = await storage_service.save_upload(
        file,
        category="uploads/images",
        allowed_extensions={"jpg", "jpeg", "png", "webp"},
        max_size_mb=settings.upload_image_max_mb,
    )
    return success_response(UploadResponse(url=url).model_dump())


@router.post("/audio")
async def upload_audio(
    _: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    url = await storage_service.save_upload(
        file,
        category="uploads/audio",
        allowed_extensions={"mp3", "wav", "m4a", "ogg"},
        max_size_mb=settings.upload_audio_max_mb,
    )
    return success_response(UploadResponse(url=url).model_dump())
