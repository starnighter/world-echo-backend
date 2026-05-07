from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.config import Settings


class PromptRefinerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def refine_from_audio_features(
        self,
        *,
        audio_features: dict[str, Any],
        asr_text: str | None,
        extra_prompt: str | None,
    ) -> dict[str, Any]:
        if self.settings.mock_vision_prompt or not self.settings.siliconflow_api_url:
            combined = ", ".join(
                part
                for part in [
                    extra_prompt or "",
                    f"tempo {audio_features.get('bpm')}",
                    "/".join(audio_features.get("genre", [])),
                    "/".join(audio_features.get("tags", [])),
                    asr_text or "",
                ]
                if part
            )
            return {
                "style_prompt": combined or "cinematic pop with emotional vocals",
                "summary": "mock-refined",
            }

        system_prompt = (
            "你是音乐生成提示词工程师。根据音频分析结果和 ASR 文本，"
            "生成一个适合 MiniMax 音乐生成模型的 JSON，格式为 "
            '{"style_prompt":"...", "summary":"..."}。'
        )
        payload = {
            "audio_features": audio_features,
            "asr_text": asr_text,
            "extra_prompt": extra_prompt,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.settings.siliconflow_api_url,
                headers={"Authorization": f"Bearer {self.settings.siliconflow_api_key}"},
                json={
                    "model": self.settings.siliconflow_model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return self._parse_json_payload(content)

    @staticmethod
    def _parse_json_payload(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
