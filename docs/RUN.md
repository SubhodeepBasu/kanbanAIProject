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
