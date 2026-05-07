from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any
from urllib.parse import quote

import httpx
import websockets
from fastapi import WebSocket

from app.core.config import Settings
from app.core.exceptions import BadRequestException


class ASRService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, file_bytes: bytes, filename: str, language: str | None = None) -> dict[str, Any]:
        if self.settings.mock_asr or not self.settings.asr_api_url:
            return {
                "text": f"mock transcript for {filename}",
                "language": language or "zh",
                "duration": round(max(len(file_bytes) / 16000, 1.0), 2),
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.settings.asr_api_url,
                headers={"Authorization": f"Bearer {self.settings.asr_api_key}"},
                files={"file": (filename, file_bytes)},
                data={"language": language or "zh"},
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "text": payload.get("text", ""),
                "language": payload.get("language", language or "zh"),
                "duration": float(payload.get("duration", 0)),
            }

    async def bridge_stream(self, websocket: WebSocket, language: str = "zh") -> None:
        if self.settings.mock_asr or not (self.settings.xfyun_app_id and self.settings.xfyun_api_key):
            await self._mock_bridge_stream(websocket, language)
            return

        target_url = self._build_xfyun_url()
        async with websockets.connect(target_url, max_size=None) as upstream:
            receive_task = asyncio.create_task(self._forward_upstream_messages(websocket, upstream))
            try:
                await websocket.send_json({"event": "started", "language": language})
                while True:
                    message = await websocket.receive()
                    if "bytes" in message and message["bytes"] is not None:
                        await upstream.send(message["bytes"])
                    elif message.get("text"):
                        text = message["text"]
                        if text == "__end__":
                            await upstream.send(json.dumps({"end": True}))
                            break
                    else:
                        break
            finally:
                receive_task.cancel()

    async def _mock_bridge_stream(self, websocket: WebSocket, language: str) -> None:
        chunk_count = 0
        await websocket.send_json({"event": "started", "language": language})
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"] is not None:
                chunk_count += 1
                await websocket.send_json(
                    {
                        "event": "result",
                        "text": f"mock partial transcript {chunk_count}",
                        "is_final": False,
                    }
                )
            elif message.get("text") == "__end__":
                await websocket.send_json(
                    {
                        "event": "result",
                        "text": "mock final transcript",
                        "is_final": True,
                    }
                )
                break
            else:
                break

    async def _forward_upstream_messages(self, websocket: WebSocket, upstream) -> None:
        async for message in upstream:
            await self._relay_xfyun_message(websocket, message)

    async def _relay_xfyun_message(self, websocket: WebSocket, message: str) -> None:
        payload = json.loads(message)
        action = payload.get("action")
        if action == "started":
            return
        if action == "result":
            transcript = self._extract_xfyun_text(payload.get("data", ""))
            await websocket.send_json(
                {
                    "event": "result",
                    "text": transcript,
                    "is_final": False,
                    "raw": payload,
                }
            )
            return
        if action == "error":
            await websocket.send_json(
                {
                    "event": "error",
                    "text": payload.get("desc") or payload.get("message") or "xfyun error",
                    "raw": payload,
                }
            )
            return
        await websocket.send_json({"event": "raw", "raw": payload})

    def _extract_xfyun_text(self, raw_data: str) -> str:
        try:
            outer = json.loads(raw_data)
            segments = outer.get("cn", {}).get("st", {}).get("rt", [])
            words: list[str] = []
            for segment in segments:
                for ws_item in segment.get("ws", []):
                    for candidate in ws_item.get("cw", []):
                        word = candidate.get("w")
                        if word:
                            words.append(word)
            if words:
                return "".join(words)
        except Exception:
            pass

        matches = re.findall(r'"w":"(.*?)"', raw_data)
        return "".join(matches)

    def _build_xfyun_url(self) -> str:
        ts = str(int(time.time()))
        base = hashlib.md5((self.settings.xfyun_app_id + ts).encode("utf-8")).hexdigest().encode("utf-8")
        signa = base64.b64encode(
            hmac.new(self.settings.xfyun_api_key.encode("utf-8"), base, hashlib.sha1).digest()
        ).decode("utf-8")
        return (
            f"{self.settings.xfyun_rtasr_url}?appid={self.settings.xfyun_app_id}"
            f"&ts={ts}&signa={quote(signa)}"
        )
