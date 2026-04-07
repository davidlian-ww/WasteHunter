@echo off
echo.
echo ========================================
echo   TIMWOOD Waste Dashboard Launcher
echo ========================================
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check if database exists, if not run seed data
if not exist timwood.db (
    echo First time setup - creating sample data...
    python seed_data.py
    echo.
)

REM Start the server
echo Starting TIMWOOD Dashboard...
echo.
echo Dashboard will open at: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start server and open browser
start http://localhost:8000
python run.py

pause
