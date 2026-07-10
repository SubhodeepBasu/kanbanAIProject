$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
docker compose up --build -d
Write-Host 'Service started at http://localhost:8000'
