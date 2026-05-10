from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
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
        audio_base64: str | None = None,
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
            "stream": audio_base64 is None,
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
        if audio_base64:
            payload["audio_base64"] = audio_base64

        timeout = httpx.Timeout(connect=20.0, read=300.0, write=20.0, pool=20.0)
        if audio_base64:
            async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
                response = await client.post(
                    self.settings.minimax_api_url,
                    headers=headers,
                    json=payload,
                )
                self._raise_for_minimax_error(response)
                item = response.json()
                self._ensure_minimax_success(item)
                music_data = item.get("data") or {}
                audio_hex = music_data.get("audio")
                if not audio_hex:
                    raise UnprocessableException("MiniMax generation returned empty audio")
                yield GeneratedChunk(
                    status=2,
                    audio_hex=audio_hex,
                    extra_info=self._normalize_extra_info(item.get("extra_info")),
                )
                return

        saw_final_chunk = False
        streamed_audio_parts: list[str] = []
        last_extra_info: dict[str, Any] | None = None
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            async with client.stream("POST", self.settings.minimax_api_url, headers=headers, json=payload) as response:
                self._raise_for_minimax_error(response)
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = line[5:] if line.startswith("data:") else line
                    if data.strip() == "[DONE]":
                        if streamed_audio_parts and not saw_final_chunk:
                            saw_final_chunk = True
                            yield GeneratedChunk(
                                status=2,
                                audio_hex="".join(streamed_audio_parts),
                                extra_info=last_extra_info,
                            )
                        break
                    item = httpx.Response(200, text=data).json()
                    self._ensure_minimax_success(item)
                    music_data = item.get("data") or {}
                    audio_hex = music_data.get("audio")
                    extra_info = self._normalize_extra_info(item.get("extra_info"))
                    if extra_info:
                        last_extra_info = extra_info

                    raw_status = music_data.get("status")
                    if raw_status is None:
                        if audio_hex:
                            streamed_audio_parts.append(audio_hex)
                            yield GeneratedChunk(status=1, audio_hex=None, extra_info=None)
                        continue

                    status = int(raw_status)
                    saw_final_chunk = status == 2
                    if audio_hex and not saw_final_chunk:
                        streamed_audio_parts.append(audio_hex)
                    yield GeneratedChunk(
                        status=status,
                        audio_hex=audio_hex or "".join(streamed_audio_parts) if saw_final_chunk else None,
                        extra_info=extra_info,
                    )
                    if saw_final_chunk:
                        break

                if streamed_audio_parts and not saw_final_chunk:
                    yield GeneratedChunk(
                        status=2,
                        audio_hex="".join(streamed_audio_parts),
                        extra_info=last_extra_info,
                    )

    async def _mock_stream_generate(self, *, model: str, prompt: str, lyrics: str | None) -> AsyncIterator[GeneratedChunk]:
        final_audio = self._load_mock_audio_bytes()
        chunk_size = max(1, len(final_audio) // 3)
        chunks = [
            final_audio[index:index + chunk_size]
            for index in range(0, len(final_audio), chunk_size)
        ]
        for payload in chunks[:-1]:
            await asyncio.sleep(0.01)
            yield GeneratedChunk(status=1, audio_hex=payload.hex(), extra_info=None)
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

    def _load_mock_audio_bytes(self) -> bytes:
        sample = self._find_mock_audio_sample()
        if sample is not None:
            return sample.read_bytes()
        raise UnprocessableException("No mock audio sample available")

    def _find_mock_audio_sample(self) -> Path | None:
        music_root = self.settings.storage_root / "generated" / "music"
        if not music_root.exists():
            return None
        for candidate in sorted(music_root.rglob("*.mp3")):
            if candidate.stat().st_size > 1024:
                return candidate
        return None

    @staticmethod
    def _raise_for_minimax_error(response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        message = response.text
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            base_resp = payload.get("base_resp") or {}
            message = (
                base_resp.get("status_msg")
                or payload.get("message")
                or payload.get("error")
                or message
            )
        raise UnprocessableException(str(message))

    @staticmethod
    def _ensure_minimax_success(item: dict[str, Any]) -> None:
        base_resp = item.get("base_resp") or {}
        if base_resp.get("status_code") not in (None, 0):
            raise UnprocessableException(
                base_resp.get("status_msg", "MiniMax generation failed")
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
