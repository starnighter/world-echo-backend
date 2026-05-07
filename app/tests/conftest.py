from pathlib import Path

import pytest

from app.core.config import get_settings
from app.services.asr_service import ASRService
from app.services.music_generation_service import MusicGenerationService
from app.services.storage_service import StorageService


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def settings(tmp_path: Path):
    settings = get_settings()
    settings.storage_root = tmp_path / "storage"
    settings.static_root = settings.storage_root
    settings.mock_asr = True
    settings.mock_minimax = True
    settings.mock_audio_analysis = True
    settings.mock_vision_prompt = True
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return settings


@pytest.fixture
def storage_service(settings):
    return StorageService(settings)


@pytest.fixture
def asr_service(settings):
    return ASRService(settings)


@pytest.fixture
def music_generation_service(settings):
    return MusicGenerationService(settings)
