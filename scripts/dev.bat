@echo off
set "PROJECT_ROOT=%~dp0.."

start "Frontend - Dev" /D "%PROJECT_ROOT%" cmd /k "npm run dev"
start "Backend - Dev" /D "%PROJECT_ROOT%\backend" cmd /k "uv run -m uvicorn app.main:app --port 2454"
