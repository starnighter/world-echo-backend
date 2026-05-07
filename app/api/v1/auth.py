from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.responses import success_response
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    AuthTokenResponse,
    LoginRequest,
    OAuthCallbackResponse,
    OAuthUrlResponse,
    RegisterRequest,
    UpdateMeRequest,
)
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService


router = APIRouter()
settings = get_settings()
oauth_service = OAuthService(settings)
auth_service = AuthService()


@router.post("/register")
async def register(payload: RegisterRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    token, user = await auth_service.register(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
    )
    return success_response(AuthTokenResponse(token=token, user=auth_service.to_profile(user)).model_dump(mode="json"))


@router.post("/login")
async def login(payload: LoginRequest, db: Annotated[AsyncSession, Depends(get_db)]):
    token, user = await auth_service.login_with_password(
        db,
        account=payload.account,
        password=payload.password,
    )
    return success_response(AuthTokenResponse(token=token, user=auth_service.to_profile(user)).model_dump(mode="json"))


@router.get("/oauth/{provider}/url")
async def get_oauth_url(provider: str):
    url = await oauth_service.build_url(provider)
    return success_response(OAuthUrlResponse(url=url).model_dump())


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, code: str, db: Annotated[AsyncSession, Depends(get_db)]):
    identity = await oauth_service.fetch_identity(provider, code)
    token, user, is_new_user = await auth_service.login_with_oauth(db, identity)
    payload = OAuthCallbackResponse(
        token=token,
        user=auth_service.to_profile(user),
        is_new_user=is_new_user,
    )
    return success_response(payload.model_dump(mode="json"))


@router.post("/logout")
async def logout():
    return success_response(None)


@router.get("/me")
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return success_response(auth_service.to_profile(current_user).model_dump(mode="json"))


@router.put("/me")
async def update_me(
    payload: UpdateMeRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    user = await auth_service.update_profile(
        db,
        current_user,
        username=payload.username,
        email=payload.email,
        avatar_url=payload.avatar_url,
    )
    return success_response(auth_service.to_profile(user).model_dump(mode="json"))
