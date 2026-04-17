@echo off
REM ─────────────────────────────────────────────────────────────────
REM  install_startup.bat  —  run ONCE to make Waster Hunter auto-start
REM  on every Windows login.  No admin rights needed.
REM ─────────────────────────────────────────────────────────────────

SET LAUNCHER=%~dp0start_waster_hunter.bat
SET STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
SET SHORTCUT=%STARTUP%\WasterHunter.bat

echo Installing Waster Hunter auto-start...
echo Startup folder: %STARTUP%
echo.

REM Just copy the launcher into the user Startup folder
copy /Y "%LAUNCHER%" "%SHORTCUT%" >nul

IF EXIST "%SHORTCUT%" (
    echo [OK] Waster Hunter will now start automatically on login.
    echo.
    echo To REMOVE auto-start, delete:
    echo    %SHORTCUT%
) ELSE (
    echo [FAILED] Could not write to startup folder.
    echo Try running as Administrator.
)

echo.
pause
