@echo off
setlocal
cd /d "%~dp0\.."
docker compose up --build -d
if errorlevel 1 exit /b %errorlevel%
echo Service started at http://localhost:8000
