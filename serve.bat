@echo off
:: TIMWOOD FMO Dashboard - Production launcher
:: Double-click to start. Share the URL with your floor leaders.
:: Keep this window open while your team is using the dashboard.

title TIMWOOD FMO Dashboard

cd /d "%~dp0"

:: Detect this machine's LAN IP (first non-loopback IPv4)
for /f "tokens=*" %%i in ('powershell -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike '*Loopback*' -and $_.IPAddress -notlike '169.*'} | Select-Object -First 1).IPAddress"') do set MY_IP=%%i

echo.
echo  ============================================================
echo   TIMWOOD FMO Dashboard  -  TIMWOOD Waste Tracker
echo  ============================================================
echo.
echo   Server is starting...
echo.
echo   Share this URL with your floor leaders:
echo.
echo     http://%MY_IP%:8001
echo.
echo   They must be on Eagle WiFi or Walmart VPN to connect.
echo   Keep this window open while your team is using the app.
echo.
echo  ============================================================
echo.

:: Start in production mode (no reload, stable for multi-user)
.venv\Scripts\python.exe run_prod.py

echo.
echo  Server stopped. Press any key to exit.
pause >nul
