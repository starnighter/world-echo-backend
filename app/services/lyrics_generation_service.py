from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.core.config import Settings
from app.core.exceptions import UnprocessableException


@dataclass
class LyricsGenerationResult:
    song_title: str | None
    style_tags: str | None
    lyrics: str


class LyricsGenerationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_full_song(
        self,
        *,
        prompt: str,
        title: str | None = None,
    ) -> LyricsGenerationResult:
        if self.settings.mock_minimax or not self.settings.minimax_api_key:
            return LyricsGenerationResult(
                song_title=title,
                style_tags=None,
                lyrics="",
            )

        payload: dict[str, str] = {
            "mode": "write_full_song",
            "prompt": prompt[:2000],
        }
        if title:
            payload["title"] = title

        timeout = httpx.Timeout(connect=20.0, read=120.0, write=20.0, pool=20.0)
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            response = await client.post(
                self.settings.minimax_lyrics_api_url,
                headers={
                    "Authorization": f"Bearer {self.settings.minimax_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        base_resp = data.get("base_resp") or {}
        if base_resp.get("status_code") not in (None, 0):
            raise UnprocessableException(base_resp.get("status_msg", "MiniMax lyrics generation failed"))

        lyrics = (data.get("lyrics") or "").strip()
        if not lyrics:
            raise UnprocessableException("MiniMax lyrics generation returned empty lyrics")

        return LyricsGenerationResult(
            song_title=(data.get("song_title") or "").strip() or title,
            style_tags=(data.get("style_tags") or "").strip() or None,
            lyrics=lyrics,
        )
