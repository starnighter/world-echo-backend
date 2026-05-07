from __future__ import annotations

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
            response = await client.post(
                self.settings.siliconflow_api_url,
                headers={"Authorization": f"Bearer {self.settings.siliconflow_api_key}"},
                json={
                    "model": self.settings.siliconflow_model,
                    "image_path": str(image_path),
                    "extra_prompt": extra_prompt,
                },
            )
            response.raise_for_status()
            return response.json()
