from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

import httpx

from app.core.config import Settings


class VisionPromptService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def analyze_image(self, image_path: Path, extra_prompt: str | None = None) -> dict[str, Any]:
        if self.settings.mock_vision_prompt or not self.settings.siliconflow_api_url:
            base_prompt = "cinematic ambient pop, warm textures, emotional and melodic"
            if extra_prompt:
                base_prompt = f"{base_prompt}, {extra_prompt}"
            return {
                "scene": image_path.stem,
                "objects": ["sky", "light", "subject"],
                "mood": "warm",
                "style_prompt": base_prompt,
            }

        async with httpx.AsyncClient(timeout=60.0) as client:
            image_data_url = self._image_to_data_url(image_path)
            text_prompt = (
                "你是专业音乐提示词工程师。请根据图片内容生成音乐生成提示词，返回 JSON，"
                '包含 scene, objects, mood, style_prompt 四个字段。style_prompt 应是可直接输入音乐模型的中文描述。'
            )
            if extra_prompt:
                text_prompt += f" 同时融合用户补充要求：{extra_prompt}"
            response = await client.post(
                self.settings.siliconflow_api_url,
                headers={"Authorization": f"Bearer {self.settings.siliconflow_api_key}"},
                json={
                    "model": self.settings.siliconflow_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": image_data_url}},
                                {"type": "text", "text": text_prompt},
                            ],
                        }
                    ],
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            return self._parse_json_payload(content)

    @staticmethod
    def _image_to_data_url(image_path: Path) -> str:
        encoded = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        return f"data:image/{image_path.suffix.lstrip('.').lower()};base64,{encoded}"

    @staticmethod
    def _parse_json_payload(content: str) -> dict[str, Any]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
        return json.loads(cleaned)
