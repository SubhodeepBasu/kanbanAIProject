# Backend Agent Notes

## Purpose

Backend hosts FastAPI APIs and serves static content for the Project Management MVP.

## Current status (Part 9 scaffold)

- Entry point: `main.py`
- Health endpoint: `GET /api/health`
- Board read endpoint: `GET /api/board?username=user`
- Board write endpoint: `PUT /api/board?username=user`
- AI connectivity endpoint: `GET /api/ai/test` (use `live=true` for real OpenRouter call)
- AI board actions endpoint: `POST /api/ai/board`
- Static hello page: `GET /hello`
- Frontend static export is served at `/` when `frontend/out` exists.
- SQLite database initializes automatically on startup.
- OpenRouter default model configured: `qwen/qwen3-coder:free`.
- OpenRouter fallback model for 429 retry: `openai/gpt-4o-mini`.
- Dependency management inside container: `uv`

## Local container behavior

- Runs `uvicorn main:app` on port `8000`.
- Designed to be started via docker compose and scripts in `scripts/`.
- In container, exported frontend files are copied to `/app/frontend/out`.
- In container, database defaults to `/data/pm.db`.

## Next expected evolutions

- Add frontend AI sidebar integration for chat and auto-apply board updates.