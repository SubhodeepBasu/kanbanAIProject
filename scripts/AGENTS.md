# Scripts Agent Notes

This folder contains start/stop scripts for Windows, macOS, and Linux.

## Files

- Windows PowerShell: `start.ps1`, `stop.ps1`
- Windows CMD: `start.bat`, `stop.bat`
- macOS/Linux bash: `start.sh`, `stop.sh`

## Behavior

- Scripts run from repo root and use `docker compose`.
- Start scripts build and launch container in detached mode.
- Stop scripts bring the compose project down.