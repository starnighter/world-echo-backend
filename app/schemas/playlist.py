from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.song import SongSummary


class PlaylistCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    cover_url: str | None = None
    is_public: bool = False


class PlaylistUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    cover_url: str | None = None
    is_public: bool | None = None


class AddSongToPlaylistRequest(BaseModel):
    song_id: str


class PlaylistSortItem(BaseModel):
    song_id: str
    sort_order: int


class SortPlaylistSongsRequest(BaseModel):
    items: list[PlaylistSortItem]


class PlaylistSummary(BaseModel):
    id: int
    title: str
    description: str | None = None
    cover_url: str | None = None
    is_public: bool
    is_default: bool
    songs_count: int
    created_at: datetime


class PlaylistDetail(BaseModel):
    id: int
    title: str
    description: str | None = None
    cover_url: str | None = None
    is_public: bool
    is_default: bool
    songs_count: int
    created_at: datetime
    updated_at: datetime
    songs: list[SongSummary]
