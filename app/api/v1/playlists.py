from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.playlist import (
    AddSongToPlaylistRequest,
    PlaylistCreateRequest,
    PlaylistUpdateRequest,
    SortPlaylistSongsRequest,
)
from app.services.playlist_service import PlaylistService


router = APIRouter()
playlist_service = PlaylistService()


@router.get("")
async def list_playlists(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    playlists = await playlist_service.list_playlists(db, current_user)
    payload = {
        "items": [playlist_service.to_summary(item).model_dump(mode="json") for item in playlists],
        "total": len(playlists),
    }
    return success_response(payload)


@router.post("")
async def create_playlist(
    payload: PlaylistCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    playlist = await playlist_service.create_playlist(
        db,
        current_user,
        payload.title,
        payload.description,
        payload.cover_url,
        payload.is_public,
    )
    full = await playlist_service.get_playlist(db, current_user, playlist.id)
    return success_response(playlist_service.to_detail(full).model_dump(mode="json"))


@router.get("/{playlist_id}")
async def get_playlist(
    playlist_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    playlist = await playlist_service.get_playlist(db, current_user, playlist_id)
    return success_response(playlist_service.to_detail(playlist).model_dump(mode="json"))


@router.put("/{playlist_id}")
async def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    playlist = await playlist_service.update_playlist(
        db,
        current_user,
        playlist_id,
        title=payload.title,
        description=payload.description,
        cover_url=payload.cover_url,
        is_public=payload.is_public,
    )
    full = await playlist_service.get_playlist(db, current_user, playlist.id)
    return success_response(playlist_service.to_detail(full).model_dump(mode="json"))


@router.delete("/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await playlist_service.delete_playlist(db, current_user, playlist_id)
    return success_response(None)


@router.post("/{playlist_id}/songs")
async def add_song(
    playlist_id: int,
    payload: AddSongToPlaylistRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await playlist_service.add_song(db, current_user, playlist_id, UUID(payload.song_id))
    playlist = await playlist_service.get_playlist(db, current_user, playlist_id)
    return success_response(playlist_service.to_detail(playlist).model_dump(mode="json"))


@router.delete("/{playlist_id}/songs/{song_id}")
async def remove_song(
    playlist_id: int,
    song_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await playlist_service.remove_song(db, current_user, playlist_id, song_id)
    return success_response(None)


@router.post("/{playlist_id}/songs/sort")
async def sort_songs(
    playlist_id: int,
    payload: SortPlaylistSongsRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    await playlist_service.sort_songs(
        db,
        current_user,
        playlist_id,
        [(UUID(item.song_id), item.sort_order) for item in payload.items],
    )
    playlist = await playlist_service.get_playlist(db, current_user, playlist_id)
    return success_response(playlist_service.to_detail(playlist).model_dump(mode="json"))
