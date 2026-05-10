from typing import Annotated
from uuid import UUID

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import UnauthorizedException
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedException("Authorization required")
    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException("Token invalid or expired")
    result = await db.execute(select(User).options(selectinload(User.oauths)).where(User.id == UUID(subject)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException("User not found")
    return user


async def get_current_user_from_bearer_or_query(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    access_token: Annotated[str | None, Query()] = None,
) -> User:
    token = credentials.credentials if credentials is not None else access_token
    if not token:
        raise UnauthorizedException("Authorization required")
    payload = decode_access_token(token)
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException("Token invalid or expired")
    result = await db.execute(select(User).options(selectinload(User.oauths)).where(User.id == UUID(subject)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedException("User not found")
    return user


async def get_optional_user(
    db: Annotated[AsyncSession, Depends(get_db)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User | None:
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        subject = payload.get("sub")
        if not subject:
            return None
        result = await db.execute(select(User).options(selectinload(User.oauths)).where(User.id == UUID(subject)))
        return result.scalar_one_or_none()
    except Exception:
        return None
