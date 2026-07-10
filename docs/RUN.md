# Local Run (Part 2 scaffold)

## Start

From repository root:

- PowerShell: `./scripts/start.ps1`
- CMD: `scripts\\start.bat`
- macOS/Linux: `./scripts/start.sh`

## Stop

From repository root:

- PowerShell: `./scripts/stop.ps1`
- CMD: `scripts\\stop.bat`
- macOS/Linux: `./scripts/stop.sh`

## Smoke checks

After startup:

- Hello page: `http://localhost:8000/hello`
- Health API: `http://localhost:8000/api/health`

Expected health JSON:

```json
{"status":"ok","service":"pm-backend"}
```

## Frontend E2E tests (simpler setup)

- E2E tests are configured to run against installed Google Chrome channel.
- Command: `npm run test:e2e` (from `frontend/`).
- If Chrome is missing, install Chrome and rerun; no Playwright Chromium cache management is required.

## AI connectivity check (Part 8)

- Route: `GET /api/ai/test`
- Default mode (`live=false`): returns readiness metadata without calling OpenRouter.
- Live mode (`live=true`): runs a real `2+2` prompt against OpenRouter.
- If the requested/default model returns HTTP 429, backend retries once with fallback model `openai/gpt-4o-mini`.

Example (PowerShell):

```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/ai/test" -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri "http://localhost:8000/api/ai/test?live=true" -UseBasicParsing | Select-Object -ExpandProperty Content
```

Required for live mode:

- `OPENROUTER_API_KEY` must be available to backend runtime.
- Model used by default: `qwen/qwen3-coder:free`.

## AI board actions (Part 9)

- Route: `POST /api/ai/board`
- Body: `{ "prompt": "..." }`
- Optional query params:
	- `username` (default `user`)
	- `model` (defaults to backend model)

Example (PowerShell):

```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:8000/api/ai/board" -ContentType "application/json" -Body '{"prompt":"Rename Backlog to Ideas and add a planning card."}' -UseBasicParsing | Select-Object -ExpandProperty Content
```

Response includes:

- `assistantMessage`
- `operationsApplied`
- `board` (updated state)
- `model`, `requestedModel`, `fallbackUsed`
