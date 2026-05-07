from typing import Annotated
from uuid import UUID

from fastapi import Depends
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
