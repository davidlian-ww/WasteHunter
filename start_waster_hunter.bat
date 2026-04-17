@echo off
REM ─────────────────────────────────────────────────────────────────
REM  Waster Hunter — one-click launcher
REM  Double-click this file to start the server in the background.
REM  Floor leaders connect via Eagle WiFi at the URL shown in the
REM  Share page: http://localhost:8001/share
REM ─────────────────────────────────────────────────────────────────

SET APP_DIR=%~dp0timwood-dashboard
SET PYTHON=%~dp0timwood-dashboard\.venv\Scripts\python.exe
SET LOG=%~dp0server.log

echo Starting Waster Hunter...
echo Log: %LOG%
echo.

REM Kill any existing instance on port 8001 (not Teams on 8080!)
FOR /F "tokens=5" %%P IN ('netstat -ano ^| findstr ":8001.*LISTEN" 2^>nul') DO (
    taskkill /PID %%P /F /T >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM Start the server detached (window stays hidden)
start "WasterHunter" /B cmd /C "cd /d %APP_DIR% && %PYTHON% -m uvicorn app.main:app --host 0.0.0.0 --port 8001 > %LOG% 2>&1"

REM Wait a moment then open the share page
timeout /t 4 /nobreak >nul
start http://localhost:8001/share

echo Waster Hunter is running!
echo Open http://localhost:8001 on any Eagle WiFi device.
