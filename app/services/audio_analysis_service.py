from __future__ import annotations

import json
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
        import numpy as np
        from essentia.standard import (
            KeyExtractor,
            MonoLoader,
            RhythmExtractor2013,
            TensorflowPredict2D,
            TensorflowPredictEffnetDiscogs,
        )

        audio_44k = MonoLoader(filename=str(audio_path), sampleRate=44100, resampleQuality=4)()
        audio_16k = MonoLoader(filename=str(audio_path), sampleRate=16000, resampleQuality=4)()
        bpm, beats, beat_confidence, _, _ = RhythmExtractor2013(method="multifeature")(audio_44k)
        key, scale, key_strength = KeyExtractor(sampleRate=44100, profileType="bgate")(audio_44k)
        genre = self._predict_labels(
            audio_16k,
            self.settings.models_dir / "genre_discogs400-discogs-effnet-1.pb",
            self.settings.models_dir / "genre_discogs400-discogs-effnet-1.json",
            TensorflowPredictEffnetDiscogs,
            TensorflowPredict2D,
            np,
            top_k=5,
        )
        tags = self._predict_labels(
            audio_16k,
            self.settings.models_dir / "mtg_jamendo_top50tags-discogs-effnet-1.pb",
            self.settings.models_dir / "mtg_jamendo_top50tags-discogs-effnet-1.json",
            TensorflowPredictEffnetDiscogs,
            TensorflowPredict2D,
            np,
            top_k=8,
        )
        return {
            "duration_sec": round(len(audio_44k) / 44100, 2),
            "bpm": round(float(bpm), 2),
            "beat_count": len(beats),
            "beat_confidence": round(float(beat_confidence), 4),
            "key": {"tonic": key, "scale": scale, "strength": round(float(key_strength), 4)},
            "genre": [item["label"] for item in genre],
            "genre_scores": genre,
            "tags": [item["label"] for item in tags],
            "tag_scores": tags,
            "source_file": audio_path.name,
        }

    def _predict_labels(
        self,
        audio_16k,
        classifier_pb: Path,
        classifier_json: Path,
        effnet_cls,
        predict2d_cls,
        np_module,
        *,
        top_k: int,
    ) -> list[dict[str, Any]]:
        embeddings = effnet_cls(
            graphFilename=str(self.settings.models_dir / "discogs-effnet-bs64-1.pb"),
            output="PartitionedCall:1",
        )(audio_16k)
        classifier = predict2d_cls(
            graphFilename=str(classifier_pb),
            input="serving_default_model_Placeholder",
            output="PartitionedCall:0",
        )
        predictions = classifier(embeddings)
        scores = np_module.mean(predictions, axis=0) if getattr(predictions, "ndim", 1) > 1 else predictions
        metadata = json.loads(classifier_json.read_text(encoding="utf-8"))
        classes = metadata["classes"]
        indices = np_module.argsort(scores)[::-1][:top_k]
        return [{"label": str(classes[i]), "score": float(scores[i])} for i in indices]
