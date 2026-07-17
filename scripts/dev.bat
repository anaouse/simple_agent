@echo off
set "PROJECT_ROOT=%~dp0.."

rem Stop deployed frontend and backend processes by their listening ports.
for %%R in (5000 2453) do (
    for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%%R .*LISTENING"') do (
        taskkill /F /PID %%P >nul 2>&1
    )
)

start "Frontend - Dev" /D "%PROJECT_ROOT%" cmd /k "npm run dev"
start "Backend - Dev" /D "%PROJECT_ROOT%\backend" cmd /k "uv run -m uvicorn app.main:app --reload --port 2453"
