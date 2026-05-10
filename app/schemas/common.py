from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class UploadResponse(BaseModel):
    url: str


class SSESongPayload(BaseModel):
    status: int
    song_id: str | None = None
    phase: str | None = None
    progress: float | None = None
    message: str | None = None
    extra_info: dict[str, Any] | None = None


class TimestampedModel(ORMModel):
    created_at: datetime
    updated_at: datetime
