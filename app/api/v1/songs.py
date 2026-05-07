from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.song import PublishSongRequest, SongListResponse, SongUpdateRequest
from app.services.song_service import SongService


router = APIRouter()
song_service = SongService()


@router.get("")
async def list_songs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
):
    items, total = await song_service.list_songs(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        source_type=source_type,
    )
    payload = SongListResponse(
        items=[song_service.to_summary(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
    return success_response(payload.model_dump(mode="json"))


@router.get("/{song_id}")
async def get_song(
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    song = await song_service.get_owned_song(db, current_user, song_id)
    return success_response(song_service.to_detail(song).model_dump(mode="json"))


@router.put("/{song_id}")
async def update_song(
    song_id: UUID,
    payload: SongUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    song = await song_service.update_song(db, current_user, song_id, payload.title, payload.description)
    return success_response(song_service.to_detail(song).model_dump(mode="json"))


@router.delete("/{song_id}")
async def delete_song(
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await song_service.delete_song(db, current_user, song_id)
    return success_response(None)


@router.post("/{song_id}/publish")
async def publish_song(
    song_id: UUID,
    payload: PublishSongRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    song = await song_service.publish_song(db, current_user, song_id, payload.is_public)
    return success_response(song_service.to_detail(song).model_dump(mode="json"))
