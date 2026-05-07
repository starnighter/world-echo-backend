from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class OAuthUrlResponse(BaseModel):
    url: str


class OAuthBinding(ORMModel):
    provider: str
    created_at: datetime


class UserProfile(ORMModel):
    id: str
    username: str
    email: EmailStr | None = None
    avatar_url: str | None = None
    is_banned: bool
    created_at: datetime | None = None
    oauths: list[OAuthBinding] = []


class OAuthCallbackResponse(BaseModel):
    token: str
    user: UserProfile
    is_new_user: bool


class UpdateMeRequest(BaseModel):
    username: str | None = Field(default=None, min_length=2, max_length=50)
    email: EmailStr | None = None
    avatar_url: str | None = None
