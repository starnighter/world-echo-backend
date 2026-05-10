from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_from_bearer_or_query
from app.core.config import get_settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.responses import success_response
from app.db.models import Song, User
from app.db.session import get_db
from app.schemas.song import PublishSongRequest, SongListResponse, SongUpdateRequest
from app.services.song_service import SongService
from app.services.storage_service import StorageService


router = APIRouter()
song_service = SongService()
settings = get_settings()
storage_service = StorageService(settings)


@router.get("")
async def list_songs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status: str | None = Query(default=None),
    source_type: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    items, total = await song_service.list_songs(
        db,
        current_user,
        page=page,
        page_size=page_size,
        status=status,
        source_type=source_type,
        keyword=keyword,
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


@router.get("/{song_id}/stream")
async def stream_song(
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user_from_bearer_or_query)],
):
    """Stream audio file with proper range-request support.

    Uses FileResponse so Starlette sends the file in chunks via
    aiofiles instead of loading it entirely into memory.
    """
    song = await db.get(Song, song_id)
    if song is None or song.deleted_at is not None:
        raise NotFoundException("Song not found")
    if song.user_id != current_user.id and not song.is_public:
        raise ForbiddenException("No permission to access this song")
    if not song.music_url:
        return success_response(None)

    # Resolve the relative music_url (e.g. "/static/generated/music/…")
    # to an absolute path on disk.
    prefix = f"{settings.static_url}/"
    if song.music_url.startswith(prefix):
        rel = song.music_url.removeprefix(prefix)
    else:
        rel = song.music_url.lstrip("/")
    file_path: Path = settings.storage_root / rel

    if not file_path.is_file():
        return success_response(None)
    try:
        storage_service.normalize_mp3_payload(file_path.read_bytes())
    except Exception as exc:
        raise NotFoundException("Song audio file is invalid") from exc

    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        filename=f"{song.title or 'song'}.mp3",
    )


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
