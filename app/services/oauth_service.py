from __future__ import annotations

import secrets
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode

import httpx

from app.core.config import Settings
from app.core.exceptions import BadRequestException


@dataclass
class OAuthIdentity:
    provider: str
    provider_uid: str
    username: str
    email: str | None
    avatar_url: str | None


class OAuthService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build_url(self, provider: str) -> str:
        if provider == "github":
            params = {
                "client_id": self.settings.github_client_id or "mock-github-client",
                "redirect_uri": self.settings.github_redirect_uri,
                "scope": "read:user user:email",
                "state": secrets.token_urlsafe(16),
            }
            return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
        if provider == "qq":
            params = {
                "response_type": "code",
                "client_id": self.settings.qq_client_id or "mock-qq-client",
                "redirect_uri": self.settings.qq_redirect_uri,
                "scope": self.settings.qq_scope,
                "state": secrets.token_urlsafe(16),
            }
            return f"https://graph.qq.com/oauth2.0/authorize?{urlencode(params)}"
        raise BadRequestException("Unsupported OAuth provider")

    async def fetch_identity(self, provider: str, code: str) -> OAuthIdentity:
        if self.settings.mock_oauth:
            suffix = code[-6:] if code else "mocked"
            return OAuthIdentity(
                provider=provider,
                provider_uid=f"{provider}-{suffix}",
                username=f"{provider}_user_{suffix}",
                email=f"{provider}_{suffix}@example.com",
                avatar_url=f"https://cdn.world-echo.com/mock/{provider}/{suffix}.png",
            )
        if provider == "github":
            return await self._fetch_github_identity(code)
        if provider == "qq":
            return await self._fetch_qq_identity(code)
        raise BadRequestException("Unsupported OAuth provider")

    async def _fetch_github_identity(self, code: str) -> OAuthIdentity:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": self.settings.github_client_id,
                    "client_secret": self.settings.github_client_secret,
                    "code": code,
                    "redirect_uri": self.settings.github_redirect_uri,
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")
            if not access_token:
                raise BadRequestException("Invalid OAuth code")

            user_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            user_resp.raise_for_status()
            user_payload = user_resp.json()
            email = user_payload.get("email")
            if not email:
                email_resp = await client.get(
                    "https://api.github.com/user/emails",
                    headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
                )
                email_resp.raise_for_status()
                emails = email_resp.json()
                primary = next((item for item in emails if item.get("primary")), None)
                email = primary.get("email") if primary else None

        return OAuthIdentity(
            provider="github",
            provider_uid=str(user_payload["id"]),
            username=user_payload.get("login") or f"github_{user_payload['id']}",
            email=email,
            avatar_url=user_payload.get("avatar_url"),
        )

    async def _fetch_qq_identity(self, code: str) -> OAuthIdentity:
        async with httpx.AsyncClient(timeout=20.0) as client:
            token_resp = await client.get(
                "https://graph.qq.com/oauth2.0/token",
                params={
                    "grant_type": "authorization_code",
                    "client_id": self.settings.qq_client_id,
                    "client_secret": self.settings.qq_client_secret,
                    "code": code,
                    "redirect_uri": self.settings.qq_redirect_uri,
                    "fmt": "json",
                },
            )
            token_resp.raise_for_status()
            token_payload = token_resp.json() if "application/json" in token_resp.headers.get("content-type", "") else parse_qs(token_resp.text)
            access_token = token_payload.get("access_token")
            if isinstance(access_token, list):
                access_token = access_token[0]
            if not access_token:
                raise BadRequestException("Invalid OAuth code")

            openid_resp = await client.get(
                "https://graph.qq.com/oauth2.0/me",
                params={"access_token": access_token, "fmt": "json"},
            )
            openid_resp.raise_for_status()
            openid_payload = openid_resp.json()
            openid = openid_payload.get("openid")
            if not openid:
                raise BadRequestException("QQ openid not found")

            user_resp = await client.get(
                "https://graph.qq.com/user/get_user_info",
                params={
                    "access_token": access_token,
                    "oauth_consumer_key": self.settings.qq_client_id,
                    "openid": openid,
                    "format": "json",
                },
            )
            user_resp.raise_for_status()
            user_payload = user_resp.json()
            if user_payload.get("ret") not in (0, None):
                raise BadRequestException(user_payload.get("msg", "QQ user info failed"))

        nickname = user_payload.get("nickname") or f"qq_{openid[:8]}"
        avatar = user_payload.get("figureurl_qq_2") or user_payload.get("figureurl_2") or user_payload.get("figureurl")
        return OAuthIdentity(
            provider="qq",
            provider_uid=openid,
            username=nickname,
            email=None,
            avatar_url=avatar,
        )
