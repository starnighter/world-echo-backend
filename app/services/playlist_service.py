from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException, UnprocessableException
from app.db.models import Playlist, PlaylistItem, Song, User
from app.schemas.playlist import PlaylistDetail, PlaylistSummary
from app.services.song_service import SongService


class PlaylistService:
    def __init__(self) -> None:
        self.song_service = SongService()

    async def list_playlists(self, db: AsyncSession, user: User) -> list[Playlist]:
        stmt = (
            select(Playlist)
            .where(Playlist.user_id == user.id, Playlist.deleted_at.is_(None))
            .order_by(Playlist.is_default.desc(), Playlist.created_at.asc())
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.song))
        )
        return list((await db.execute(stmt)).scalars().unique().all())

    async def create_playlist(self, db: AsyncSession, user: User, title: str, description: str | None, cover_url: str | None, is_public: bool) -> Playlist:
        playlist = Playlist(
            user_id=user.id,
            title=title,
            description=description,
            cover_url=cover_url,
            is_public=is_public,
            is_default=False,
        )
        db.add(playlist)
        await db.commit()
        await db.refresh(playlist)
        return playlist

    async def get_playlist(self, db: AsyncSession, user: User, playlist_id: int) -> Playlist:
        stmt = (
            select(Playlist)
            .where(Playlist.id == playlist_id, Playlist.deleted_at.is_(None))
            .options(selectinload(Playlist.items).selectinload(PlaylistItem.song))
        )
        playlist = (await db.execute(stmt)).scalar_one_or_none()
        if playlist is None:
            raise NotFoundException("Playlist not found")
        if playlist.user_id != user.id:
            raise ForbiddenException("No permission to access this playlist")
        return playlist

    async def update_playlist(self, db: AsyncSession, user: User, playlist_id: int, **updates) -> Playlist:
        playlist = await self.get_playlist(db, user, playlist_id)
        for key, value in updates.items():
            if value is not None:
                setattr(playlist, key, value)
        await db.commit()
        await db.refresh(playlist)
        return playlist

    async def delete_playlist(self, db: AsyncSession, user: User, playlist_id: int) -> None:
        playlist = await self.get_playlist(db, user, playlist_id)
        if playlist.is_default:
            raise UnprocessableException("Default playlist cannot be deleted")
        playlist.deleted_at = datetime.now(UTC)
        await db.commit()

    async def add_song(self, db: AsyncSession, user: User, playlist_id: int, song_id: UUID) -> PlaylistItem:
        playlist = await self.get_playlist(db, user, playlist_id)
        song = await db.get(Song, song_id)
        if song is None or song.deleted_at is not None:
            raise NotFoundException("Song not found")
        if song.user_id != user.id and not song.is_public:
            raise ForbiddenException("No permission to add this song")
        exists = await db.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id, PlaylistItem.song_id == song_id)
        )
        if exists.scalar_one_or_none():
            raise ConflictException("Song already exists in playlist")
        max_order = await db.execute(select(func.max(PlaylistItem.sort_order)).where(PlaylistItem.playlist_id == playlist.id))
        next_order = (max_order.scalar_one() or 0) + 1
        item = PlaylistItem(playlist_id=playlist.id, song_id=song_id, sort_order=next_order)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item

    async def remove_song(self, db: AsyncSession, user: User, playlist_id: int, song_id: UUID) -> None:
        playlist = await self.get_playlist(db, user, playlist_id)
        result = await db.execute(
            select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id, PlaylistItem.song_id == song_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            raise NotFoundException("Song is not in playlist")
        await db.delete(item)
        await db.commit()

    async def sort_songs(self, db: AsyncSession, user: User, playlist_id: int, sort_items: list[tuple[UUID, int]]) -> None:
        playlist = await self.get_playlist(db, user, playlist_id)
        result = await db.execute(select(PlaylistItem).where(PlaylistItem.playlist_id == playlist.id))
        items = {item.song_id: item for item in result.scalars().all()}
        for song_id, order in sort_items:
            if song_id not in items:
                raise NotFoundException("Song is not in playlist")
            items[song_id].sort_order = order
        await db.commit()

    @staticmethod
    def to_summary(playlist: Playlist) -> PlaylistSummary:
        songs_count = sum(
            1
            for item in playlist.items
            if item.song is not None and item.song.deleted_at is None
        )
        return PlaylistSummary(
            id=playlist.id,
            title=playlist.title,
            description=playlist.description,
            cover_url=playlist.cover_url,
            is_public=playlist.is_public,
            is_default=playlist.is_default,
            songs_count=songs_count,
            created_at=playlist.created_at,
        )

    @staticmethod
    def to_detail(playlist: Playlist) -> PlaylistDetail:
        songs = [
            SongService.to_summary(item.song)
            for item in sorted(playlist.items, key=lambda item: (item.sort_order, item.added_at))
            if item.song is not None and item.song.deleted_at is None
        ]
        return PlaylistDetail(
            id=playlist.id,
            title=playlist.title,
            description=playlist.description,
            cover_url=playlist.cover_url,
            is_public=playlist.is_public,
            is_default=playlist.is_default,
            songs_count=len(songs),
            created_at=playlist.created_at,
            updated_at=playlist.updated_at,
            songs=songs,
        )
