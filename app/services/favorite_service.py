from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, UnprocessableException
from app.db.models import Favorite, Song, User


class FavoriteService:
    async def like_song(self, db: AsyncSession, user: User, song_id: UUID) -> Favorite:
        song = await db.get(Song, song_id)
        if song is None or song.deleted_at is not None:
            raise NotFoundException("Song not found")
        if song.user_id == user.id or not song.is_public:
            raise UnprocessableException("Cannot like this song")

        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.song_id == song_id,
                Favorite.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise ConflictException("Song already liked")

        deleted = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.song_id == song_id,
                Favorite.deleted_at.is_not(None),
            )
        )
        favorite = deleted.scalar_one_or_none()
        if favorite:
            favorite.deleted_at = None
        else:
            favorite = Favorite(user_id=user.id, song_id=song_id)
            db.add(favorite)
        song.likes_count = max(0, song.likes_count + 1)
        await db.commit()
        await db.refresh(favorite)
        return favorite

    async def unlike_song(self, db: AsyncSession, user: User, song_id: UUID) -> None:
        result = await db.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.song_id == song_id,
                Favorite.deleted_at.is_(None),
            )
        )
        favorite = result.scalar_one_or_none()
        if favorite is None:
            raise NotFoundException("Favorite not found")
        song = await db.get(Song, song_id)
        if song is None:
            raise NotFoundException("Song not found")
        favorite.deleted_at = datetime.now(UTC)
        song.likes_count = max(0, song.likes_count - 1)
        await db.commit()
