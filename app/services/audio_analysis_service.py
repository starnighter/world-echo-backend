from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core.config import Settings


class AudioAnalysisService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def analyze(self, audio_path: Path) -> dict[str, Any]:
        if self.settings.mock_audio_analysis or not self.settings.enable_essentia:
            return {
                "duration_sec": 12.5,
                "bpm": 118.0,
                "key": {"tonic": "C", "scale": "major", "strength": 0.81},
                "genre": ["pop", "electronic"],
                "tags": ["energetic", "uplifting", "bright"],
                "source_file": audio_path.name,
            }
        return await self._essentia_analyze(audio_path)

    async def _essentia_analyze(self, audio_path: Path) -> dict[str, Any]:
        from essentia.standard import KeyExtractor, MonoLoader, RhythmExtractor2013

        audio = MonoLoader(filename=str(audio_path), sampleRate=44100, resampleQuality=4)()
        bpm, beats, beat_confidence, _, _ = RhythmExtractor2013(method="multifeature")(audio)
        key, scale, key_strength = KeyExtractor(sampleRate=44100, profileType="bgate")(audio)
        return {
            "duration_sec": round(len(audio) / 44100, 2),
            "bpm": round(float(bpm), 2),
            "beat_count": len(beats),
            "beat_confidence": round(float(beat_confidence), 4),
            "key": {"tonic": key, "scale": scale, "strength": round(float(key_strength), 4)},
            "genre": ["unknown"],
            "tags": ["essentia"],
            "source_file": audio_path.name,
        }
