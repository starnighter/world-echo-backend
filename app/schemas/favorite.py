from datetime import datetime

from pydantic import BaseModel


class FavoriteResponse(BaseModel):
    id: int
    song_id: str
    created_at: datetime
