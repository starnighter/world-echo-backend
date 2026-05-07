from __future__ import annotations

import secrets

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictException, UnauthorizedException, UnprocessableException
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models import Playlist, User, UserOAuth
from app.schemas.auth import OAuthBinding, UserProfile
from app.services.oauth_service import OAuthIdentity


class AuthService:
    async def register(
        self,
        db: AsyncSession,
        *,
        username: str,
        email: str | None,
        password: str,
    ) -> tuple[str, User]:
        if await self._username_exists(db, username):
            raise ConflictException("Username already exists")
        if email and await self._email_exists(db, email):
            raise ConflictException("Email already exists")

        user = User(
            username=username,
            email=email,
            password_hash=get_password_hash(password),
            is_banned=False,
        )
        db.add(user)
        await db.flush()
        await self._create_default_playlist(db, user.id)
        await db.commit()
        user = await self._get_user_with_oauths(db, user.id)
        return create_access_token(user.id), user

    async def login_with_password(self, db: AsyncSession, *, account: str, password: str) -> tuple[str, User]:
        result = await db.execute(
            select(User)
            .options(selectinload(User.oauths))
            .where(or_(User.username == account, User.email == account))
        )
        user = result.scalar_one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise UnauthorizedException("Invalid account or password")
        if user.is_banned:
            raise UnprocessableException("User has been banned")
        return create_access_token(user.id), user

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
            user = await self._get_user_with_oauths(db, oauth.user_id)
        else:
            user = await self._create_user_with_oauth(db, identity)
            is_new_user = True

        if user.is_banned:
            raise UnprocessableException("User has been banned")

        token = create_access_token(user.id)
        return token, user, is_new_user

    async def update_profile(self, db: AsyncSession, user: User, username: str | None, email: str | None, avatar_url: str | None) -> User:
        if username and username != user.username:
            if await self._username_exists(db, username, exclude_user_id=user.id):
                raise ConflictException("Username already exists")
            user.username = username
        if email is not None and email != user.email:
            if email and await self._email_exists(db, email, exclude_user_id=user.id):
                raise ConflictException("Email already exists")
            user.email = email
        if avatar_url is not None:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    def to_profile(user: User) -> UserProfile:
        return UserProfile(
            id=user.id,
            username=user.username,
            email=user.email,
            avatar_url=user.avatar_url,
            is_banned=user.is_banned,
            created_at=user.created_at,
            oauths=[
                OAuthBinding(provider=oauth.provider, created_at=oauth.created_at)
                for oauth in getattr(user, "oauths", [])
            ],
        )

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
        await self._create_default_playlist(db, user.id)
        await db.commit()
        return await self._get_user_with_oauths(db, user.id)

    async def _unique_username(self, db: AsyncSession, base_name: str) -> str:
        candidate = base_name[:50] or "user"
        for _ in range(10):
            if not await self._username_exists(db, candidate):
                return candidate
            candidate = f"{base_name[:42]}_{secrets.token_hex(3)}"
        raise ConflictException("Unable to allocate username")

    async def _get_user_with_oauths(self, db: AsyncSession, user_id) -> User:
        result = await db.execute(select(User).options(selectinload(User.oauths)).where(User.id == user_id))
        user = result.scalar_one()
        return user

    async def _username_exists(self, db: AsyncSession, username: str, exclude_user_id=None) -> bool:
        stmt = select(User.id).where(User.username == username)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _email_exists(self, db: AsyncSession, email: str, exclude_user_id=None) -> bool:
        stmt = select(User.id).where(User.email == email)
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _create_default_playlist(self, db: AsyncSession, user_id) -> None:
        db.add(
            Playlist(
                user_id=user_id,
                title="我的收藏",
                is_default=True,
                is_public=False,
            )
        )
