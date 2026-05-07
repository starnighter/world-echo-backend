from __future__ import annotations

import base64
import json
from pathlib import Path
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
        spectrogram_path: Path | None = None,
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

        feature_payload = dict(audio_features)
        if asr_text:
            feature_payload["asr_text"] = asr_text
        if extra_prompt:
            feature_payload["extra_prompt"] = extra_prompt

        feature_text = json.dumps(feature_payload, ensure_ascii=False, indent=2)
        user_prompt = f"""
你是一个专业音乐制作人、声音设计师和音乐生成提示词工程师。

下面是一段输入音频的 Essentia 分析结果，以及它的频谱图。

你的任务：
根据这些信息，生成一个适合输入给“音乐生成模型”的提示词。
这个提示词要让音乐生成模型创作出一段与原音频风格、质感、节奏、频谱分布和氛围相似的完整音乐。

要求：
1. 不要简单复述 JSON，要转化成自然、专业的音乐生成 prompt。
2. 描述音乐风格、情绪、速度、节奏、音色、频谱特征、动态、空间感、结构建议。
3. 如果输入音频更像白噪音、环境声、氛围音或纹理音，不要强行写旋律与和弦，要强调 texture、ambient、noise、drone、soundscape。
4. 如果调性、和弦、音高置信度较弱，要说明“无明确旋律中心”或“弱调性”。
5. 不要要求复制原曲，不要生成侵权描述，只描述可泛化的音乐特征。
6. 输出中文提示词，同时附带一个英文版 prompt。
7. 最终输出 JSON，格式如下：

{{
  "中文提示词": "...",
  "English Prompt": "...",
  "适合的音乐生成参数建议": {{
    "duration": "...",
    "tempo": "...",
    "genre": "...",
    "mood": "...",
    "instrumentation": "...",
    "production_style": "..."
  }}
}}

音频分析结果如下：

{feature_text}
"""

        content: list[dict[str, Any]] = []
        if spectrogram_path and spectrogram_path.exists():
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self._image_to_data_url(spectrogram_path)},
                }
            )
        content.append({"type": "text", "text": user_prompt})
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.settings.siliconflow_api_url,
                headers={"Authorization": f"Bearer {self.settings.siliconflow_api_key}"},
                json={
                    "model": self.settings.siliconflow_model,
                    "messages": [
                        {"role": "user", "content": content},
                    ],
                    "temperature": 0.4,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = self._parse_json_payload(content)
            style_prompt = parsed.get("中文提示词") or parsed.get("style_prompt") or ""
            english_prompt = parsed.get("English Prompt")
            summary = parsed.get("适合的音乐生成参数建议") or parsed.get("summary")
            return {
                "style_prompt": style_prompt,
                "english_prompt": english_prompt,
                "summary": summary,
                "raw": parsed,
            }

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
