from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_user
from app.core.exceptions import NotFoundException
from app.core.responses import success_response
from app.db.models import Favorite, Song, User
from app.db.session import get_db
from app.schemas.plaza import PlazaListResponse, PlazaSongItem
from app.services.song_service import SongService


router = APIRouter()


@router.get("")
async def list_plaza(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_user)],
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    keyword: str | None = Query(default=None),
):
    base_filter = [Song.is_public.is_(True), Song.deleted_at.is_(None)]
    if keyword:
        pattern = f"%{keyword}%"
        base_filter.append(Song.title.ilike(pattern))
    stmt = (
        select(Song, User.username, User.avatar_url)
        .join(User, Song.user_id == User.id)
        .where(*base_filter)
        .order_by(Song.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    count_stmt = select(func.count()).select_from(Song).where(*base_filter)
    rows = (await db.execute(stmt)).all()
    total = (await db.execute(count_stmt)).scalar_one()

    # Get liked song IDs for current user
    liked_ids: set = set()
    if current_user is not None:
        song_ids = [song.id for song, _, _ in rows]
        if song_ids:
            like_stmt = select(Favorite.song_id).where(
                Favorite.user_id == current_user.id,
                Favorite.song_id.in_(song_ids),
                Favorite.deleted_at.is_(None),
            )
            liked_ids = set((await db.execute(like_stmt)).scalars().all())

    items = [
        PlazaSongItem(
            **SongService.to_summary(song).model_dump(mode="json"),
            user={"username": username, "avatar_url": avatar_url},
            is_liked=song.id in liked_ids,
        )
        for song, username, avatar_url in rows
    ]
    payload = PlazaListResponse(items=items, total=total, page=page, page_size=page_size)
    return success_response(payload.model_dump(mode="json"))


@router.get("/{song_id}")
async def plaza_detail(song_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]):
    song = await db.get(Song, song_id)
    if song is None or song.deleted_at is not None or not song.is_public:
        raise NotFoundException("Song not found")
    # Get user info
    user = await db.get(User, song.user_id)
    detail = SongService.to_detail(song).model_dump(mode="json")
    if user is not None:
        detail["user"] = {"username": user.username, "avatar_url": user.avatar_url}
    return success_response(detail)
