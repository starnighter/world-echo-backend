import os
import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


TEST_STORAGE_ROOT = Path("/tmp/world_echo_test_storage")

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@127.0.0.1:5433/world_echo",
)
os.environ.setdefault("MOCK_OAUTH", "true")
os.environ.setdefault("MOCK_ASR", "true")
os.environ.setdefault("MOCK_VISION_PROMPT", "true")
os.environ.setdefault("MOCK_AUDIO_ANALYSIS", "true")
os.environ.setdefault("MOCK_MINIMAX", "true")
os.environ.setdefault("STORAGE_ROOT", str(TEST_STORAGE_ROOT))
os.environ.setdefault("STATIC_ROOT", str(TEST_STORAGE_ROOT))
os.environ.setdefault("PUBLIC_BASE_URL", "http://testserver")

from app.core.config import get_settings
from app.main import app
from app.services.asr_service import ASRService
from app.services.music_generation_service import MusicGenerationService
from app.services.storage_service import StorageService


@pytest.fixture(scope="session", autouse=True)
def prepare_test_environment() -> Iterator[None]:
    TEST_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    yield
    shutil.rmtree(TEST_STORAGE_ROOT, ignore_errors=True)


@pytest.fixture(autouse=True)
def reset_state() -> Iterator[None]:
    get_settings.cache_clear()
    TEST_STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    _truncate_tables()
    _clear_storage()
    yield
    _truncate_tables()
    _clear_storage()
    get_settings.cache_clear()


def _clear_storage() -> None:
    if TEST_STORAGE_ROOT.exists():
        for child in TEST_STORAGE_ROOT.iterdir():
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)


def _truncate_tables() -> None:
    subprocess.run(
        [
            "docker",
            "exec",
            "world-echo-backend-db-1",
            "psql",
            "-U",
            "postgres",
            "-d",
            "world_echo",
            "-c",
            "TRUNCATE TABLE favorites, playlist_items, playlists, songs, user_oauths, users RESTART IDENTITY CASCADE;",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
def storage_service(settings):
    return StorageService(settings)


@pytest.fixture
def asr_service(settings):
    return ASRService(settings)


@pytest.fixture
def music_generation_service(settings):
    return MusicGenerationService(settings)


@pytest.fixture
def auth_headers(client: TestClient):
    response = client.get("/v1/auth/oauth/github/callback?code=test-user")
    payload = response.json()
    token = payload["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def parse_sse_events(response_text: str) -> list[dict]:
    events: list[dict] = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            import json

            events.append(json.loads(line[6:]))
    return events
