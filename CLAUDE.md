# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-user Project Management MVP: a Kanban board with drag-and-drop, an AI chat sidebar that can create/edit/move/delete cards and rename columns, hardcoded login (`user`/`password`), one board per user. NextJS frontend (static export) served by a FastAPI backend, packaged into one Docker container, SQLite for storage. See `AGENTS.md` (root) for full business requirements and color scheme, and `docs/PLAN.md` for the part-by-part build history and current status notes.

## Commands

### Frontend (`frontend/`)

- `npm run dev` — dev server (port 3000)
- `npm run build` — static export (writes `frontend/out`, consumed by the backend)
- `npm run lint`
- `npm run test:unit` (alias `npm test`) — Vitest unit/component tests
- `npm run test:unit:watch` — Vitest watch mode
- `npm run test:e2e` — Playwright, against **Chrome channel** (not bundled Chromium), targeting `http://127.0.0.1:8000` by default (the FastAPI server, not `next dev`) — override with `E2E_BASE_URL`
- `npm run test:all` — unit then e2e
- Single Vitest test: `npx vitest run src/lib/kanban.test.ts` (or `-t "name"` to filter)
- Single Playwright test: `npx playwright test tests/kanban.spec.ts`
- Coverage: `npx vitest run --coverage`

### Backend (`backend/`)

- Run dev server: `uvicorn main:app --reload --port 8000` (from `backend/`)
- Install deps: `uv pip install --system -r requirements.txt -r requirements-dev.txt` (or plain `pip install`)
- All tests: `python -m pytest -q`
- Single test file: `python -m pytest tests/test_ai_actions.py -q`
- Single test: `python -m pytest tests/test_db.py::test_name -q`
- Coverage: `python -m pytest --cov=. --cov-report=term-missing -q`

### Whole app (Docker)

- Start: `./scripts/start.ps1` / `.bat` / `.sh` (repo root) — builds and runs via `docker compose`, exposes port 8000
- Stop: `./scripts/stop.ps1` / `.bat` / `.sh`
- Smoke check: `GET /hello`, `GET /api/health`
- `OPENROUTER_API_KEY` is provided via root `.env` (loaded by docker-compose's `env_file`)

## Architecture

**Build/serve model:** the frontend is built with `next build` (`output: "export"` in `next.config.ts`) into `frontend/out`, a pure static site with no Node server involved at runtime. The Dockerfile builds this in a `node` stage, then copies `frontend/out` into the Python runtime image. FastAPI (`backend/main.py`) mounts that directory as `StaticFiles` at `/` *after* registering all `/api/*` routes, so API routes always take precedence over the static mount. Locally (non-Docker), `create_app()` looks for `../frontend/out` relative to `backend/main.py`, or `FRONTEND_DIST_DIR` if set — Playwright's default `baseURL` of `127.0.0.1:8000` assumes this static build exists, which is why e2e needs a build first (or the Docker container running), not just `next dev`.

**Backend module boundaries** (`backend/`):
- `main.py` — FastAPI app/route wiring only (`create_app()` factory, takes optional `frontend_dist_dir`/`db_path` overrides used by tests).
- `db.py` — all SQLite access. Board state is stored as **one JSON blob per user** (`boards.board_json`), not normalized tables; see `docs/DB_MODEL.md` for the schema and rationale. `init_database()` creates tables and seeds a default `user`/board on first run.
- `ai.py` — OpenRouter HTTP calls only (`call_openrouter_prompt`, connectivity test, and `run_board_action_prompt` which sends the full board + a strict-JSON system prompt and returns the parsed `{assistantMessage, operations}` payload). Default model `qwen/qwen3-coder:free`; on a 429 it retries once with fallback `openai/gpt-4o-mini`. The frontend's AI sidebar (`src/lib/api.ts`) pins `model=openai/gpt-4o-mini` directly for reliability rather than relying on the fallback path.
- `ai_actions.py` — pure functions with no I/O: validates the AI's JSON payload shape and applies its `operations` (`create_card`, `edit_card`, `move_card`, `delete_card`, `rename_column`) to a board dict via `apply_board_operations`, returning a new board (deep-copied, never mutates the input).

The AI board-edit flow end to end: frontend posts a prompt → `main.py` loads the current board from `db.py` → `ai.py` calls OpenRouter with the board embedded in the prompt → `ai_actions.py` validates and applies the returned operations → if any applied, the new board is persisted via `db.py` and returned to the frontend, which replaces its local board state wholesale (no merge logic on the client).

**Frontend structure** (`frontend/src/`):
- `app/page.tsx` → `components/AuthGate.tsx` (sessionStorage-based fake login, gates everything) → `components/KanbanBoard.tsx` (owns all board state, fetches/saves via `lib/api.ts`, wires up `@dnd-kit` drag-and-drop, and renders `AiSidebar`).
- `lib/kanban.ts` is the single source of truth for the `BoardData`/`Card`/`Column` shape and pure board-mutation logic (`moveCard`); this shape must match `backend/db.py`'s `default_board()` and what `ai_actions.py` operates on — if you change one, update all three.
- `lib/api.ts` is the only place that calls backend HTTP endpoints; components never call `fetch` directly.
- Every board mutation (drag, rename, add/delete card, AI action) goes through `KanbanBoard`'s `applyBoardChange`, which updates local state and fires a `saveBoard` PUT in the background — the backend is not the source of truth during a session, local state is, and a failed save just surfaces an error banner rather than rolling back.

## Coding standards (from root `AGENTS.md`)

- Keep it simple — no over-engineering, no unnecessary defensive programming, no speculative features.
- No emojis, anywhere.
- When debugging, find the root cause with evidence before applying a fix; don't guess.
