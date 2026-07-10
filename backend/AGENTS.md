# Backend Agent Notes

## Purpose

Backend hosts FastAPI APIs and serves static content for the Project Management MVP.

## Current status (Part 6 scaffold)

- Entry point: `main.py`
- Health endpoint: `GET /api/health`
- Board read endpoint: `GET /api/board?username=user`
- Board write endpoint: `PUT /api/board?username=user`
- Static hello page: `GET /hello`
- Frontend static export is served at `/` when `frontend/out` exists.
- SQLite database initializes automatically on startup.
- Dependency management inside container: `uv`

## Local container behavior

- Runs `uvicorn main:app` on port `8000`.
- Designed to be started via docker compose and scripts in `scripts/`.
- In container, exported frontend files are copied to `/app/frontend/out`.
- In container, database defaults to `/data/pm.db`.

## Next expected evolutions

- Add OpenRouter AI endpoints.