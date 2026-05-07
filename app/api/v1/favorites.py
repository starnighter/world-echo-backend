from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.favorite import FavoriteResponse
from app.services.favorite_service import FavoriteService


router = APIRouter()
favorite_service = FavoriteService()


@router.post("/{song_id}")
async def like_song(
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    favorite = await favorite_service.like_song(db, current_user, song_id)
    payload = FavoriteResponse(id=favorite.id, song_id=str(favorite.song_id), created_at=favorite.created_at)
    return success_response(payload.model_dump(mode="json"))


@router.delete("/{song_id}")
async def unlike_song(
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await favorite_service.unlike_song(db, current_user, song_id)
    return success_response(None)
