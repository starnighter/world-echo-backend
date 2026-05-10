from __future__ import annotations

import asyncio
import contextlib
import json
import math
import time
import uuid
from array import array
from typing import Any
from urllib.parse import urlencode

import httpx
import websockets
from fastapi import WebSocket
from websockets import ConnectionClosed

from app.core.config import Settings
from app.core.exceptions import BadRequestException


class ASRService:
    LASR_SLICE_LEN = 5 * 1024 * 1024
    PCM_BYTES_PER_SECOND = 32000

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def transcribe(self, file_bytes: bytes, filename: str, language: str | None = None) -> dict[str, Any]:
        if self.settings.mock_asr or not self.settings.vivo_app_key:
            return {
                "text": f"mock transcript for {filename}",
                "language": language or "zh",
                "duration": round(max(len(file_bytes) / 16000, 1.0), 2),
            }

        return await self._transcribe_with_vivo_lasr(file_bytes, filename, language or "zh")

    async def bridge_stream(self, websocket: WebSocket, language: str = "zh") -> None:
        if self.settings.mock_asr or not self.settings.vivo_app_key:
            await self._mock_bridge_stream(websocket, language)
            return

        await websocket.send_json({"event": "started", "language": language})
        buffered_chunks: list[bytes] = []
        buffered_bytes = 0
        upstream = None
        receive_task = None
        finished = asyncio.Event()
        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"] is not None:
                    chunk = message["bytes"]
                    if upstream is None:
                        buffered_chunks.append(chunk)
                        buffered_bytes += len(chunk)
                        if buffered_bytes >= self._min_realtime_pcm_bytes:
                            rejection_reason = self._realtime_buffer_rejection_reason(b"".join(buffered_chunks))
                            if rejection_reason is not None:
                                await websocket.send_json({"event": "error", "text": rejection_reason})
                                finished.set()
                                break
                            upstream = await self._open_vivo_realtime_upstream()
                            receive_task = asyncio.create_task(
                                self._forward_upstream_messages(websocket, upstream, finished)
                            )
                            for buffered_chunk in buffered_chunks:
                                await upstream.send(buffered_chunk)
                            buffered_chunks.clear()
                    else:
                        await upstream.send(chunk)
                elif message.get("text"):
                    text = message["text"]
                    if text == "__end__":
                        if upstream is None:
                            await websocket.send_json(
                                {
                                    "event": "error",
                                    "text": (
                                        f"Audio stream too short; minimum duration is "
                                        f"{self.settings.vivo_realtime_min_seconds:.1f}s"
                                    ),
                                }
                            )
                            finished.set()
                            break
                        try:
                            await upstream.send(b"--end--")
                        except ConnectionClosed:
                            pass
                        with contextlib.suppress(asyncio.TimeoutError):
                            await asyncio.wait_for(finished.wait(), timeout=10)
                        break
                else:
                    break
        finally:
            if upstream is not None:
                with contextlib.suppress(ConnectionClosed):
                    await upstream.send(b"--close--")
                await upstream.close()
            if receive_task is not None:
                receive_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await receive_task

    async def _mock_bridge_stream(self, websocket: WebSocket, language: str) -> None:
        chunk_count = 0
        total_bytes = 0
        buffered_chunks: list[bytes] = []
        await websocket.send_json({"event": "started", "language": language})
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"] is not None:
                chunk_count += 1
                chunk = message["bytes"]
                total_bytes += len(chunk)
                buffered_chunks.append(chunk)
                if total_bytes >= self._min_realtime_pcm_bytes:
                    rejection_reason = self._realtime_buffer_rejection_reason(b"".join(buffered_chunks))
                    if rejection_reason is not None:
                        await websocket.send_json({"event": "error", "text": rejection_reason})
                        break
                    await websocket.send_json(
                        {
                            "event": "result",
                            "text": f"mock partial transcript {chunk_count}",
                            "is_final": False,
                        }
                    )
            elif message.get("text") == "__end__":
                if total_bytes < self._min_realtime_pcm_bytes:
                    await websocket.send_json(
                        {
                            "event": "error",
                            "text": (
                                f"Audio stream too short; minimum duration is "
                                f"{self.settings.vivo_realtime_min_seconds:.1f}s"
                            ),
                        }
                    )
                    break
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

    async def _forward_upstream_messages(self, websocket: WebSocket, upstream, finished: asyncio.Event) -> None:
        async for message in upstream:
            await self._relay_vivo_short_asr_message(websocket, message, finished)

    async def _relay_vivo_short_asr_message(
        self, websocket: WebSocket, message: str, finished: asyncio.Event
    ) -> None:
        payload = json.loads(message)
        action = payload.get("action")
        if action == "started":
            return
        if action == "result":
            data = payload.get("data", {})
            is_final = bool(data.get("is_last", False))
            await websocket.send_json(
                {
                    "event": "result",
                    "text": data.get("text", ""),
                    "is_final": is_final,
                    "raw": payload,
                }
            )
            if is_final:
                finished.set()
            return
        if action == "error":
            await websocket.send_json(
                {
                    "event": "error",
                    "text": payload.get("desc") or payload.get("message") or "vivo asr error",
                    "raw": payload,
                }
            )
            finished.set()
            return
        if action == "vad":
            await websocket.send_json({"event": "vad", "raw": payload})
            return
        await websocket.send_json({"event": "raw", "raw": payload})

    async def _transcribe_with_vivo_lasr(
        self, file_bytes: bytes, filename: str, language: str
    ) -> dict[str, Any]:
        x_session_id = uuid.uuid4().hex
        audio_id, slice_num = await self._vivo_lasr_create(file_bytes, x_session_id)
        await self._vivo_lasr_upload(file_bytes, filename, audio_id, x_session_id, slice_num)
        task_id = await self._vivo_lasr_run(audio_id, x_session_id)
        await self._vivo_lasr_wait_for_completion(task_id, x_session_id)
        result_payload = await self._vivo_lasr_result(task_id, x_session_id)
        transcript = self._extract_vivo_lasr_text(result_payload)
        if not transcript:
            raise BadRequestException("Unable to recognize speech from the uploaded audio")
        return {
            "text": transcript,
            "language": language,
            "duration": round(max(len(file_bytes) / 16000, 1.0), 2),
        }

    async def _vivo_lasr_create(self, file_bytes: bytes, x_session_id: str) -> tuple[str, int]:
        slice_num = max(1, (len(file_bytes) + self.LASR_SLICE_LEN - 1) // self.LASR_SLICE_LEN)
        payload = {
            "audio_type": "auto",
            "x-sessionId": x_session_id,
            "slice_num": slice_num,
        }
        response = await self._vivo_lasr_post(
            "/create",
            params=self._build_vivo_lasr_params(),
            json_body=payload,
            headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        if response.get("action") == "error":
            raise BadRequestException(response.get("desc") or "vivo lasr create failed")
        data = response.get("data") or {}
        audio_id = data.get("audio_id")
        if not audio_id:
            raise BadRequestException("vivo lasr create did not return audio_id")
        return str(audio_id), slice_num

    async def _vivo_lasr_upload(
        self,
        file_bytes: bytes,
        filename: str,
        audio_id: str,
        x_session_id: str,
        slice_num: int,
    ) -> None:
        for slice_index in range(slice_num):
            start = slice_index * self.LASR_SLICE_LEN
            end = start + self.LASR_SLICE_LEN
            params = self._build_vivo_lasr_params(
                audio_id=audio_id,
                x_session_id=x_session_id,
                slice_index=slice_index,
            )
            response = await self._vivo_lasr_post(
                "/upload",
                params=params,
                files={"file": (filename, file_bytes[start:end], "application/octet-stream")},
                headers={"Accept": "*/*"},
            )
            if response.get("action") == "error":
                raise BadRequestException(response.get("desc") or f"vivo lasr upload failed at slice {slice_index}")

    async def _vivo_lasr_run(self, audio_id: str, x_session_id: str) -> str:
        response = await self._vivo_lasr_post(
            "/run",
            params=self._build_vivo_lasr_params(),
            json_body={"audio_id": audio_id, "x-sessionId": x_session_id},
            headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        if response.get("action") == "error":
            raise BadRequestException(response.get("desc") or "vivo lasr run failed")
        data = response.get("data") or {}
        task_id = data.get("task_id")
        if not task_id:
            raise BadRequestException("vivo lasr run did not return task_id")
        return str(task_id)

    async def _vivo_lasr_wait_for_completion(self, task_id: str, x_session_id: str) -> None:
        for _ in range(60):
            await asyncio.sleep(2)
            response = await self._vivo_lasr_post(
                "/progress",
                params=self._build_vivo_lasr_params(),
                json_body={"task_id": task_id, "x-sessionId": x_session_id},
                headers={"Content-Type": "application/json; charset=UTF-8"},
            )
            if response.get("action") == "error":
                raise BadRequestException(response.get("desc") or "vivo lasr progress failed")
            data = response.get("data") or {}
            if int(data.get("progress", 0)) >= 100:
                return
        raise BadRequestException("vivo lasr transcription timed out")

    async def _vivo_lasr_result(self, task_id: str, x_session_id: str) -> dict[str, Any]:
        response = await self._vivo_lasr_post(
            "/result",
            params=self._build_vivo_lasr_params(),
            json_body={"task_id": task_id, "x-sessionId": x_session_id},
            headers={"Content-Type": "application/json; charset=UTF-8"},
        )
        if response.get("action") == "error":
            raise BadRequestException(response.get("desc") or "vivo lasr result failed")
        return response

    async def _vivo_lasr_post(
        self,
        path: str,
        *,
        params: dict[str, str],
        json_body: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.settings.vivo_lasr_base_url}{path}"
        request_headers = {"Authorization": f"Bearer {self.settings.vivo_app_key}"}
        if headers:
            request_headers.update(headers)
        async with httpx.AsyncClient(timeout=120.0, trust_env=False) as client:
            response = await client.post(
                url,
                params=params,
                headers=request_headers,
                json=json_body,
                files=files,
            )
            response.raise_for_status()
            return response.json()

    def _build_vivo_short_asr_url(self) -> str:
        params = {
            "client_version": "unknown",
            "product": "x",
            "package": self.settings.vivo_app_package,
            "sdk_version": "unknown",
            "user_id": self.settings.vivo_user_id,
            "android_version": "unknown",
            "system_time": str(int(round(time.time() * 1000))),
            "net_type": "1",
            "engineid": self.settings.vivo_short_asr_engine_id,
            "requestId": str(uuid.uuid4()),
        }
        return f"{self.settings.vivo_asr_ws_url}?{urlencode(params)}"

    def _build_vivo_lasr_params(
        self,
        *,
        audio_id: str | None = None,
        x_session_id: str | None = None,
        slice_index: int | None = None,
    ) -> dict[str, str]:
        params = {
            "client_version": "2.0",
            "package": self.settings.vivo_app_package,
            "user_id": self.settings.vivo_user_id,
            "system_time": str(int(round(time.time() * 1000))),
            "net_type": "1",
            "engineid": self.settings.vivo_long_asr_engine_id,
            "requestId": str(uuid.uuid4()),
        }
        if audio_id is not None:
            params["audio_id"] = audio_id
        if x_session_id is not None:
            params["x-sessionId"] = x_session_id
        if slice_index is not None:
            params["slice_index"] = str(slice_index)
        return params

    def _extract_vivo_lasr_text(self, payload: dict[str, Any]) -> str:
        data = payload.get("data")
        if isinstance(data, dict):
            direct_text = data.get("text")
            if isinstance(direct_text, str) and direct_text.strip():
                return direct_text.strip()
            result_items = data.get("result")
            if isinstance(result_items, list):
                parts = [
                    item.get("onebest", "").strip()
                    for item in result_items
                    if isinstance(item, dict) and item.get("onebest")
                ]
                if parts:
                    return "".join(parts)
            for key in ("result", "sentences", "segments", "utterances"):
                value = data.get(key)
                if isinstance(value, list):
                    parts = [
                        item.get("text", "").strip()
                        for item in value
                        if isinstance(item, dict) and item.get("text")
                    ]
                    if parts:
                        return " ".join(parts)
        found = self._find_text_strings(payload)
        return " ".join(found).strip()

    def _find_text_strings(self, value: Any) -> list[str]:
        if isinstance(value, dict):
            matches: list[str] = []
            for key, nested in value.items():
                if key == "text" and isinstance(nested, str) and nested.strip():
                    matches.append(nested.strip())
                else:
                    matches.extend(self._find_text_strings(nested))
            return matches
        if isinstance(value, list):
            matches: list[str] = []
            for item in value:
                matches.extend(self._find_text_strings(item))
            return matches
        return []

    async def _open_vivo_realtime_upstream(self):
        target_url = self._build_vivo_short_asr_url()
        upstream = await websockets.connect(
            target_url,
            additional_headers={"Authorization": f"Bearer {self.settings.vivo_app_key}"},
            max_size=None,
        )
        await upstream.send(
            json.dumps(
                {
                    "type": "started",
                    "request_id": str(uuid.uuid4()),
                    "asr_info": {
                        "front_vad_time": 6000,
                        "end_vad_time": 2000,
                        "audio_type": "pcm",
                        "chinese2digital": 1,
                        "punctuation": 2,
                    },
                    "business_info": self.settings.vivo_short_asr_business_info,
                }
            )
        )
        return upstream

    @property
    def _min_realtime_pcm_bytes(self) -> int:
        return int(self.settings.vivo_realtime_min_seconds * self.PCM_BYTES_PER_SECOND)

    def _realtime_buffer_rejection_reason(self, pcm_bytes: bytes) -> str | None:
        samples = self._pcm_samples(pcm_bytes)
        if not samples:
            return "Audio stream contains no valid PCM samples"

        rms = self._pcm_rms(samples)
        if rms < self.settings.vivo_realtime_silence_rms_threshold:
            return "Audio stream appears silent or too quiet"

        zcr = self._pcm_zero_crossing_rate(samples)
        if zcr > self.settings.vivo_realtime_noise_zcr_threshold:
            return "Audio stream appears to be noise rather than speech"

        return None

    def _pcm_samples(self, pcm_bytes: bytes) -> array[int]:
        even_length = len(pcm_bytes) - (len(pcm_bytes) % 2)
        if even_length <= 0:
            return array("h")
        samples = array("h")
        samples.frombytes(pcm_bytes[:even_length])
        return samples

    def _pcm_rms(self, samples: array[int]) -> float:
        if not samples:
            return 0.0
        squared_sum = sum(sample * sample for sample in samples)
        return math.sqrt(squared_sum / len(samples))

    def _pcm_zero_crossing_rate(self, samples: array[int]) -> float:
        if len(samples) < 2:
            return 0.0
        sign_changes = 0
        previous = samples[0]
        for current in samples[1:]:
            if (previous >= 0 > current) or (previous < 0 <= current):
                sign_changes += 1
            previous = current
        return sign_changes / (len(samples) - 1)
