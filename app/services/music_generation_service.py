from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator

import httpx

from app.core.exceptions import BadRequestException, UnprocessableException
from app.core.config import Settings


@dataclass
class GeneratedChunk:
    status: int
    audio_hex: str | None = None
    extra_info: dict[str, Any] | None = None


class MusicGenerationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def stream_generate(
        self,
        *,
        model: str,
        prompt: str,
        lyrics: str | None,
        is_instrumental: bool,
        audio_url: str | None = None,
    ) -> AsyncIterator[GeneratedChunk]:
        if self.settings.mock_minimax or not self.settings.minimax_api_key:
            async for chunk in self._mock_stream_generate(model=model, prompt=prompt, lyrics=lyrics):
                yield chunk
            return

        headers = {
            "Authorization": f"Bearer {self.settings.minimax_api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "output_format": "hex",
            "is_instrumental": is_instrumental,
            "audio_setting": {
                "sample_rate": 44100,
                "bitrate": 256000,
                "format": "mp3",
            },
        }
        if lyrics:
            payload["lyrics"] = lyrics
        elif model.startswith("music-2.6") and not is_instrumental:
            payload["lyrics_optimizer"] = True
        if audio_url:
            payload["audio_url"] = audio_url

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", self.settings.minimax_api_url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = line[5:] if line.startswith("data:") else line
                    if data.strip() == "[DONE]":
                        break
                    item = httpx.Response(200, text=data).json()
                    base_resp = item.get("base_resp") or {}
                    if base_resp.get("status_code") not in (None, 0):
                        raise UnprocessableException(base_resp.get("status_msg", "MiniMax generation failed"))
                    music_data = item.get("data") or {}
                    audio_hex = music_data.get("audio")
                    extra_info = self._normalize_extra_info(item.get("extra_info"))
                    yield GeneratedChunk(
                        status=int(music_data["status"]),
                        audio_hex=audio_hex,
                        extra_info=extra_info,
                    )

    async def _mock_stream_generate(self, *, model: str, prompt: str, lyrics: str | None) -> AsyncIterator[GeneratedChunk]:
        chunks = [
            b"ID3\x04mock-chunk-1",
            b"\xff\xfbmock-chunk-2",
            b"\xff\xfbmock-chunk-3",
        ]
        for payload in chunks:
            await asyncio.sleep(0.01)
            yield GeneratedChunk(status=1, audio_hex=payload.hex(), extra_info=None)
        final_audio = b"".join(chunks)
        yield GeneratedChunk(
            status=2,
            audio_hex=final_audio.hex(),
            extra_info={
                "duration": 32000,
                "sample_rate": 44100,
                "channel": 2,
                "bitrate": 256000,
                "size": len(final_audio),
                "model": model,
                "prompt": prompt,
                "lyrics_present": lyrics is not None,
            },
        )

    @staticmethod
    def _normalize_extra_info(extra_info: dict[str, Any] | None) -> dict[str, Any] | None:
        if not extra_info:
            return extra_info
        return {
            "duration": extra_info.get("duration", extra_info.get("music_duration")),
            "sample_rate": extra_info.get("sample_rate", extra_info.get("music_sample_rate")),
            "channel": extra_info.get("channel", extra_info.get("music_channel")),
            "bitrate": extra_info.get("bitrate"),
            "size": extra_info.get("size", extra_info.get("music_size")),
        }
