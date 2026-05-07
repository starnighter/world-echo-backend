from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FavoriteResponse(BaseModel):
    id: int
    song_id: UUID
    created_at: datetime
