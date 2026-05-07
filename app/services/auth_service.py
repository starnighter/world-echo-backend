from __future__ import annotations

import secrets

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, UnprocessableException
from app.core.security import create_access_token
from app.db.models import Playlist, User, UserOAuth
from app.schemas.auth import UserProfile
from app.services.oauth_service import OAuthIdentity


class AuthService:
    async def login_with_oauth(self, db: AsyncSession, identity: OAuthIdentity) -> tuple[str, User, bool]:
        result = await db.execute(
            select(UserOAuth).where(
                UserOAuth.provider == identity.provider,
                UserOAuth.provider_uid == identity.provider_uid,
            )
        )
        oauth = result.scalar_one_or_none()
        is_new_user = False

        if oauth is not None:
            user = await db.get(User, oauth.user_id)
            assert user is not None
        else:
            user = await self._create_user_with_oauth(db, identity)
            is_new_user = True

        if user.is_banned:
            raise UnprocessableException("User has been banned")

        token = create_access_token(user.id)
        return token, user, is_new_user

    async def update_profile(self, db: AsyncSession, user: User, username: str | None, email: str | None, avatar_url: str | None) -> User:
        if username and username != user.username:
            exists = await db.execute(select(User).where(User.username == username, User.id != user.id))
            if exists.scalar_one_or_none():
                raise ConflictException("Username already exists")
            user.username = username
        if email is not None:
            user.email = email
        if avatar_url is not None:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def to_profile(user: User) -> UserProfile:
        return UserProfile.model_validate(user)

    async def _create_user_with_oauth(self, db: AsyncSession, identity: OAuthIdentity) -> User:
        username = await self._unique_username(db, identity.username)
        user = User(
            username=username,
            email=identity.email,
            avatar_url=identity.avatar_url,
            is_banned=False,
        )
        db.add(user)
        await db.flush()

        db.add(
            UserOAuth(
                user_id=user.id,
                provider=identity.provider,
                provider_uid=identity.provider_uid,
            )
        )
        db.add(
            Playlist(
                user_id=user.id,
                title="我的收藏",
                is_default=True,
                is_public=False,
            )
        )
        await db.commit()
        await db.refresh(user)
        return user

    async def _unique_username(self, db: AsyncSession, base_name: str) -> str:
        candidate = base_name[:50] or "user"
        for _ in range(10):
            result = await db.execute(select(User.id).where(User.username == candidate))
            if result.scalar_one_or_none() is None:
                return candidate
            candidate = f"{base_name[:42]}_{secrets.token_hex(3)}"
        raise ConflictException("Unable to allocate username")
