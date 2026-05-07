from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


SourceType = Literal["image", "voice", "prompt"]
SongStatus = Literal["pending", "processing", "done", "failed"]


class SongSummary(ORMModel):
    id: UUID
    source_type: SourceType
    title: str | None = None
    description: str | None = None
    cover_url: str | None = None
    status: SongStatus
    music_url: str | None = None
    is_public: bool
    likes_count: int
    created_at: datetime
    updated_at: datetime


class SongDetail(ORMModel):
    id: UUID
    user_id: UUID
    source_type: SourceType
    extracted_data: dict[str, Any] | None = None
    model_used: str
    prompt: str | None = None
    lyrics: str | None = None
    is_instrumental: bool
    source_url: str | None = None
    title: str | None = None
    description: str | None = None
    status: SongStatus
    music_url: str | None = None
    cover_url: str | None = None
    error_msg: str | None = None
    is_public: bool
    published_at: datetime | None = None
    likes_count: int
    created_at: datetime
    updated_at: datetime


class SongListResponse(BaseModel):
    items: list[SongSummary]
    total: int
    page: int
    page_size: int


class SongUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class PublishSongRequest(BaseModel):
    is_public: bool


class BaseGenerateRequest(BaseModel):
    prompt: str | None = None
    lyrics: str | None = None
    is_instrumental: bool = False
    model_used: str | None = None


class ImageGenerateRequest(BaseGenerateRequest):
    source_url: str


class VoiceGenerateRequest(BaseGenerateRequest):
    source_url: str


class PromptGenerateRequest(BaseGenerateRequest):
    prompt: str
