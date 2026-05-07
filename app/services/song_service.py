from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException, UnprocessableException
from app.db.models import Song, User
from app.schemas.song import SongDetail, SongSummary


class SongService:
    async def create_generation_song(
        self,
        db: AsyncSession,
        *,
        user: User,
        source_type: str,
        source_url: str | None,
        prompt: str | None,
        lyrics: str | None,
        is_instrumental: bool,
        model_used: str,
    ) -> Song:
        song = Song(
            user_id=user.id,
            source_type=source_type,
            source_url=source_url,
            prompt=prompt,
            lyrics=lyrics,
            is_instrumental=is_instrumental,
            model_used=model_used,
            status="pending",
            is_public=False,
            likes_count=0,
        )
        db.add(song)
        await db.commit()
        await db.refresh(song)
        return song

    async def mark_processing(self, db: AsyncSession, song: Song) -> Song:
        song.status = "processing"
        await db.commit()
        await db.refresh(song)
        return song

    async def complete_song(
        self,
        db: AsyncSession,
        song: Song,
        *,
        music_url: str,
        cover_url: str | None,
        title: str,
        description: str | None,
        extracted_data: dict[str, Any] | None,
    ) -> Song:
        song.music_url = music_url
        song.cover_url = cover_url
        song.title = title
        song.description = description
        song.extracted_data = extracted_data
        song.status = "done"
        song.error_msg = None
        await db.commit()
        await db.refresh(song)
        return song

    async def fail_song(self, db: AsyncSession, song: Song, message: str) -> Song:
        song.status = "failed"
        song.error_msg = message
        await db.commit()
        await db.refresh(song)
        return song

    async def list_songs(
        self,
        db: AsyncSession,
        user: User,
        *,
        page: int,
        page_size: int,
        status: str | None,
        source_type: str | None,
    ) -> tuple[list[Song], int]:
        stmt = select(Song).where(Song.user_id == user.id, Song.deleted_at.is_(None))
        count_stmt = select(func.count()).select_from(Song).where(Song.user_id == user.id, Song.deleted_at.is_(None))
        if status:
            stmt = stmt.where(Song.status == status)
            count_stmt = count_stmt.where(Song.status == status)
        if source_type:
            stmt = stmt.where(Song.source_type == source_type)
            count_stmt = count_stmt.where(Song.source_type == source_type)
        stmt = stmt.order_by(Song.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()
        total = (await db.execute(count_stmt)).scalar_one()
        return rows, total

    async def get_owned_song(self, db: AsyncSession, user: User, song_id: UUID) -> Song:
        song = await db.get(Song, song_id)
        if song is None or song.deleted_at is not None:
            raise NotFoundException("Song not found")
        if song.user_id != user.id:
            raise ForbiddenException("No permission to access this song")
        return song

    async def update_song(self, db: AsyncSession, user: User, song_id: UUID, title: str | None, description: str | None) -> Song:
        song = await self.get_owned_song(db, user, song_id)
        if song.status != "done":
            raise UnprocessableException("Song is not done yet")
        if title is not None:
            song.title = title
        if description is not None:
            song.description = description
        await db.commit()
        await db.refresh(song)
        return song

    async def delete_song(self, db: AsyncSession, user: User, song_id: UUID) -> None:
        song = await self.get_owned_song(db, user, song_id)
        song.deleted_at = datetime.now(UTC)
        await db.commit()

    async def publish_song(self, db: AsyncSession, user: User, song_id: UUID, is_public: bool) -> Song:
        song = await self.get_owned_song(db, user, song_id)
        if song.status != "done":
            raise UnprocessableException("Song is not done yet")
        song.is_public = is_public
        song.published_at = datetime.now(UTC) if is_public else None
        await db.commit()
        await db.refresh(song)
        return song

    @staticmethod
    def to_detail(song: Song) -> SongDetail:
        return SongDetail.model_validate(song)

    @staticmethod
    def to_summary(song: Song) -> SongSummary:
        return SongSummary.model_validate(song)
