# Project Plan

This document is the execution checklist for the Project Management MVP.

## Global rules

- Keep implementation simple and avoid extra features.
- Aim for around 80% unit coverage when it is sensible and valuable; do not add low-value tests only to hit a number.
- Integration tests must validate end-to-end behavior between layers where applicable.
- Pause for explicit user sign-off at required approval gates.

## Part 1: Plan and alignment

### Checklist

- [x] Expand this plan with detailed checklists, tests, and success criteria for all parts.
- [x] Create frontend architecture notes in `frontend/AGENTS.md`.
- [x] Get explicit user approval of this plan before coding Part 2.

### Tests

- Manual review by user of this document and `frontend/AGENTS.md`.

### Success criteria

- All parts include concrete tasks, tests, and measurable completion conditions.
- Open assumptions are called out early.
- User confirms approval to begin Part 2.

## Part 2: Scaffolding (Docker + FastAPI + scripts)

### Checklist

- [x] Add backend FastAPI app scaffold under `backend/`.
- [x] Add Dockerfile to run FastAPI in a container (frontend serving is handled in Part 3).
- [x] Add compose file for local workflow and volume mounting.
- [x] Add scripts in `scripts/` for start/stop on Windows, macOS, and Linux.
- [x] Serve simple static hello page from backend at `/hello`.
- [x] Add sample API route (for example `/api/health`) returning JSON.
- [x] Document local run steps briefly.

### Tests

- Build container image successfully.
- Run container and verify:
	- `GET /hello` returns expected static HTML.
	- `GET /api/health` returns success JSON.
- Script smoke tests for each OS script format (syntax and expected commands).

Current status note:

- Container build/start verified successfully after Docker daemon startup.
- Live endpoint checks passed:
	- `GET /hello` -> `200`
	- `GET /api/health` -> `{"status":"ok","service":"pm-backend"}`
- Windows script smoke tests passed for `start.ps1`, `stop.ps1`, `start.bat`, and `stop.bat`.
- macOS/Linux shell scripts were authored but not executed in this Windows environment.

### Success criteria

- Single local command path starts app in Docker.
- Hello page and API endpoint are both reachable.
- Start/stop scripts are present and usable.

## Part 3: Serve existing frontend from backend

### Checklist

- [x] Build Next.js frontend as static output.
- [x] Configure FastAPI to serve generated frontend at `/`.
- [x] Keep backend API routes under `/api/*`.
- [x] Ensure static assets resolve correctly in container.

### Tests

- Unit: backend static-file serving logic and route priority.
- Integration: `GET /` renders Kanban UI with expected title and column count.
- Integration: `/api/health` still works while static app is served.

Current status note:

- Backend unit tests pass for static serving behavior and API route priority.
- Frontend unit tests pass after static-export config update.
- Docker integration checks pass:
	- `GET /` includes `Kanban Studio` content.
	- `GET /api/health` remains `{"status":"ok","service":"pm-backend"}`.
	- Referenced `/_next/*` asset URL resolves with `200`.

### Success criteria

- Root path displays existing Kanban demo.
- No broken static assets in browser.
- Backend APIs continue to respond under `/api`.

## Part 4: Fake user sign-in (client-side gating)

### Checklist

- [x] Add login screen at app entry.
- [x] Validate fixed credentials (`user` / `password`).
- [x] Gate Kanban UI behind logged-in client state.
- [x] Add logout action returning to login.

### Tests

- Unit: login form validation and state transitions.
- Integration/E2E:
	- Invalid credentials show error and do not enter app.
	- Valid credentials show Kanban board.
	- Logout returns user to login screen.

Current status note:

- Unit tests cover invalid credentials and logout transition.
- E2E now runs against installed Chrome channel (`channel: "chrome"`) to avoid fragile Playwright-managed Chromium cache issues.
- E2E scenarios pass for invalid login, valid login to board, and logout return path.

### Success criteria

- User cannot see board until valid login in current browser session.
- Login/logout flow is reliable and test-covered.

## Part 5: Database modeling (user board as one JSON blob)

### Checklist

- [x] Propose SQLite schema for one JSON board per user.
- [x] Include migration/init strategy that creates DB if missing.
- [x] Document schema and trade-offs in `docs/`.
- [x] Request user sign-off before implementation in Part 6.

### Tests

- Unit: schema initialization creates required tables/indexes.
- Manual: review documented model with user.

### Success criteria

- Clear schema with user key and JSON board payload.
- DB-init approach is documented and approved.

Current status note:

- Proposed schema, init flow, migration strategy, and trade-offs documented in `docs/DB_MODEL.md`.
- Awaiting explicit user approval (Gate B) before implementing Part 6 backend API and persistence logic.

## Part 6: Backend board API

### Checklist

- [x] Implement DB initialization on startup if file does not exist.
- [x] Add API route to fetch board for user.
- [x] Add API route to overwrite/update board JSON for user.
- [x] Keep payload contract minimal and explicit.
- [x] Add backend unit and integration tests.

### Tests

- Unit: DB read/write helpers, error handling, serialization.
- Integration:
	- Read returns seeded or saved board.
	- Write persists and is readable on next request.
	- Unknown user handling is defined and tested.

### Success criteria

- Backend can persist and retrieve one board JSON blob per user.
- DB file auto-creates when absent.
- Backend tests provide meaningful confidence for core behavior.

Current status note:

- Added SQLite init and board storage module with default `user` seed and board seed.
- Added `GET /api/board` and `PUT /api/board` endpoints with simple payload validation.
- Unknown user paths return `404`.
- Backend tests pass (8 total), including DB init, persistence roundtrip, and unknown-user handling.

## Part 7: Frontend and backend integration

### Checklist

- [x] Replace frontend in-memory board state with API-driven state.
- [x] Load board after client login.
- [x] Persist board changes (rename, add, delete, move) via backend API.
- [x] Add user-facing loading and error states.

### Tests

- Unit: API client utilities and state update behavior.
- Integration/E2E:
	- Initial board loads from backend.
	- Board edits persist across refresh/restart.
	- Network failure surfaces clear error and preserves UI stability.

### Success criteria

- Board is persistent, not demo-only memory state.
- Core Kanban operations round-trip through backend reliably.

Current status note:

- Frontend now loads board state from backend `/api/board`.
- Board updates call backend `PUT /api/board` and persist across refresh.
- Loading and backend error messages are shown in the board UI.
- Frontend unit tests pass and integrated E2E passes against backend-served app on port `8000`.

## Part 8: AI connectivity (OpenRouter)

### Checklist

- [x] Add backend AI service client for OpenRouter.
- [x] Read `OPENROUTER_API_KEY` from environment.
- [x] Configure model: `qwen/qwen3-coder:free`.
- [x] Add simple backend route/test path that runs `2+2` prompt.

### Tests

- Unit: request builder and response parser.
- Integration: live connectivity test behind env flag/opt-in execution.
- Manual: verify successful AI response for `2+2`.

### Success criteria

- Backend can call OpenRouter with configured model.
- Connectivity check is repeatable and documented.

Current status note:

- Added OpenRouter client module with request payload builder and response parser.
- Added one-time 429 fallback retry from `qwen/qwen3-coder:free` to `openai/gpt-4o-mini` for connectivity test path.
- Added `GET /api/ai/test` endpoint:
	- default (`live=false`) returns readiness metadata and usage guidance.
	- opt-in live check (`live=true`) runs OpenRouter `2+2` request using `OPENROUTER_API_KEY`.
- Configured model: `qwen/qwen3-coder:free`.
- Added unit/API tests for payload handling and endpoint behavior; backend tests pass.

## Part 9: Structured AI board actions

### Checklist

- [x] Define structured output schema with:
	- Assistant response text.
	- Optional list of board operations.
- [x] Include full board JSON and latest user prompt in AI request.
- [x] Support operation types for create/edit/move/delete card and rename column.
- [x] Apply valid operations server-side and return updated board.

### Tests

- Unit: schema validation and operation application logic.
- Integration:
	- AI response with no operations leaves board unchanged.
	- Valid operations update board as expected.
	- Invalid operations are rejected safely with clear error handling.

### Success criteria

- AI output is structured and validated before any board mutation.
- Supported operations include column renaming.

Current status note:

- Added `POST /api/ai/board` endpoint for structured AI board operations.
- AI request now includes latest user prompt and full current board JSON.
- Implemented strict payload validation for `assistantMessage` and `operations`.
- Supported operation types: `create_card`, `edit_card`, `move_card`, `delete_card`, `rename_column`.
- Server applies valid operations, persists board updates, and returns updated board state.
- Invalid operations are safely rejected with `422` and clear error details.
- Added unit and API integration tests covering no-op behavior, valid mutations, and invalid-operation rejection.

## Part 10: AI sidebar UI

### Checklist

- [x] Add sidebar chat UI to frontend.
- [x] Send user prompts to backend AI endpoint.
- [x] Render assistant replies in chat thread.
- [x] Apply returned board updates and refresh UI state automatically.
- [x] Keep layout responsive for desktop and mobile.

### Tests

- Unit: chat UI state transitions and message rendering.
- Integration/E2E:
	- User sends prompt and receives assistant reply.
	- AI-triggered board updates appear in Kanban without manual refresh.
	- Error states (timeout/API error) are visible and non-destructive.

### Success criteria

- AI sidebar is usable and stable.
- Board updates from AI appear automatically in UI.
- Test suite maintains reliable, high-value coverage for important behavior.

Current status note:

- Added right-side AI chat panel to `KanbanBoard` with responsive layout.
- Chat sends prompts to backend `POST /api/ai/board` through new frontend API client.
- Assistant replies are rendered in the sidebar thread.
- Returned board state is applied immediately in UI after AI response.
- Added frontend tests for prompt-send/reply rendering, board auto-update, and non-destructive error handling.

## Cross-cutting verification (applies throughout)

### Checklist

- [ ] Keep unit coverage healthy (target around 80% when sensible) and prioritize high-value tests.
- [ ] Add/maintain robust integration tests when a boundary changes.
- [ ] Run lint and tests before requesting review.
- [ ] Keep docs concise and updated when architecture changes.

### Core commands

- Frontend unit tests: `npm run test:unit` (in `frontend/`).
- Frontend e2e tests: `npm run test:e2e` (in `frontend/`).
- Frontend all tests: `npm run test:all` (in `frontend/`).

## Required approval gates

- Gate A (now): Plan approval for this document + `frontend/AGENTS.md`.
- Gate B: Database schema approval at end of Part 5 before Part 6 implementation.