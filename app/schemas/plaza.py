from pydantic import BaseModel

from app.schemas.song import SongSummary


class PlazaSongItem(SongSummary):
    user: dict[str, str | None]


class PlazaListResponse(BaseModel):
    items: list[PlazaSongItem]
    total: int
    page: int
    page_size: int
