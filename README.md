# World Echo Backend

## Run locally

1. Copy `.env.example` to `.env` and adjust values if needed.
2. Start PostgreSQL and API:

```bash
docker compose up --build
```

3. Open:

- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.x async ORM
- PostgreSQL + asyncpg
- JWT via `python-jose`
- `httpx` for external integrations
- Mock adapters for OAuth, ASR, vision prompt, audio analysis, and MiniMax generation

## Project structure

```text
app/
  api/
  core/
  db/
  models/
  schemas/
  services/
  tests/
```

## Implemented modules

- Auth: OAuth URL/callback, logout, current user, profile update, default playlist creation.
- Upload: image/audio upload to local static storage.
- Songs: list, detail, update, soft delete, publish/unpublish.
- Playlists: CRUD, add/remove songs, sort.
- Plaza and favorites: public feed, detail, like/unlike.
- ASR: file transcription API and realtime WebSocket bridge.
- Generation: prompt/image/voice SSE endpoints with persistent song lifecycle.

## Mock mode

Default `.env.example` keeps mock integrations enabled:

- `MOCK_OAUTH=true`
- `MOCK_ASR=true`
- `MOCK_VISION_PROMPT=true`
- `MOCK_AUDIO_ANALYSIS=true`
- `MOCK_MINIMAX=true`

This allows local API development without real third-party credentials.

## Real third-party integration

The codebase now includes real adapter paths for:

- GitHub OAuth
- QQ OAuth
- SiliconFlow prompt generation
- MiniMax music generation
- XFYun RTASR WebSocket bridge
- Essentia-based audio analysis

To switch from mock mode:

1. Set the required credentials in `.env`
2. Turn off the related `MOCK_*` flags
3. For Essentia analysis, install the optional dependency set and set `ENABLE_ESSENTIA=true`

Minimum credential set by integration:

- OAuth: `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `QQ_CLIENT_ID`, `QQ_CLIENT_SECRET`
- SiliconFlow: `SILICONFLOW_API_KEY`
- MiniMax: `MINIMAX_API_KEY`
- XFYun RTASR: `XFYUN_APP_ID`, `XFYUN_API_KEY`

## Tests

Available test files:

- `app/tests/test_core.py`
- `app/tests/test_services.py`
- `app/tests/test_generation_helpers.py`
- `app/tests/test_api_endpoints.py`
- `app/tests/test_generation_streams.py`
- `app/tests/test_websocket_asr.py`

Run after installing dev dependencies:

```bash
pip install -e .[dev]
docker compose up -d db
pytest app/tests -q
```

Integration tests expect the Docker PostgreSQL service to be reachable on host port `5433`.

## Current status

The repository now includes the backend skeleton, API modules, mock-friendly service adapters, Docker packaging, test scaffolding, and copied Essentia model assets under `app/models/`.
