from __future__ import annotations

import json
import secrets
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
        import matplotlib.pyplot as plt
        import numpy as np
        from essentia.standard import (
            FrameGenerator,
            KeyExtractor,
            MonoLoader,
            RhythmExtractor2013,
            Spectrum,
            TensorflowPredict2D,
            TensorflowPredictEffnetDiscogs,
            Windowing,
        )

        audio_44k = MonoLoader(filename=str(audio_path), sampleRate=44100, resampleQuality=4)()
        audio_16k = MonoLoader(filename=str(audio_path), sampleRate=16000, resampleQuality=4)()
        bpm, beats, beat_confidence, _, _ = RhythmExtractor2013(method="multifeature")(audio_44k)
        key, scale, key_strength = KeyExtractor(sampleRate=44100, profileType="bgate")(audio_44k)
        spectrogram_path = self._save_spectrogram(audio_44k, np, plt)
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
            "spectrogram_path": str(spectrogram_path),
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
        if getattr(embeddings, "size", len(embeddings)) == 0:
            return []
        classifier = self._build_classifier(predict2d_cls, classifier_pb)
        predictions = classifier(embeddings)
        scores = np_module.mean(predictions, axis=0) if getattr(predictions, "ndim", 1) > 1 else predictions
        metadata = json.loads(classifier_json.read_text(encoding="utf-8"))
        classes = metadata["classes"]
        indices = np_module.argsort(scores)[::-1][:top_k]
        return [{"label": str(classes[i]), "score": float(scores[i])} for i in indices]

    @staticmethod
    def _build_classifier(predict2d_cls, classifier_pb: Path):
        try:
            return predict2d_cls(
                graphFilename=str(classifier_pb),
                input="serving_default_model_Placeholder",
                output="PartitionedCall:0",
            )
        except RuntimeError:
            return predict2d_cls(
                graphFilename=str(classifier_pb),
                input="model/Placeholder",
                output="model/Sigmoid",
            )

    def _save_spectrogram(self, audio_44k, np_module, plt_module) -> Path:
        from essentia.standard import FrameGenerator, Spectrum, Windowing

        frame_size = 2048
        hop_size = 512
        window = Windowing(type="hann")
        spectrum = Spectrum(size=frame_size)
        spectrogram = []
        for frame in FrameGenerator(audio_44k, frameSize=frame_size, hopSize=hop_size):
            spectrogram.append(spectrum(window(frame)))

        spectrogram_array = np_module.array(spectrogram).T
        spectrogram_db = 20 * np_module.log10(spectrogram_array + 1e-10)

        target_dir = self.settings.storage_root / "analysis" / "spectrograms"
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{secrets.token_hex(16)}.png"

        plt_module.figure(figsize=(10, 5))
        plt_module.imshow(
            spectrogram_db,
            origin="lower",
            aspect="auto",
            extent=[0, len(audio_44k) / 44100, 0, 44100 / 2],
        )
        plt_module.xlabel("Time (s)")
        plt_module.ylabel("Frequency (Hz)")
        plt_module.title("Spectrogram")
        plt_module.colorbar(label="dB")
        plt_module.tight_layout()
        plt_module.savefig(target_path, dpi=150)
        plt_module.close()
        return target_path
