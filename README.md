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

## Current status

The repository includes the backend skeleton, API modules, mock-friendly service adapters, Docker packaging, and test scaffolding.
