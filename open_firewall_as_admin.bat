@echo off
:: TIMWOOD FMO Dashboard - One-time firewall setup
:: Double-click this file. Windows will ask for admin approval. Click Yes.

echo [TIMWOOD] Requesting admin rights to open port 8001...
echo.

powershell -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList \"-NoProfile -Command New-NetFirewallRule -DisplayName 'TIMWOOD FMO Dashboard' -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Any -Description 'Floor leader access to TIMWOOD waste dashboard'; Write-Host 'Firewall rule added! You can close this window.' -ForegroundColor Green; Start-Sleep 4\""

echo.
echo Done! Port 8001 is now open on this machine.
echo Your floor leaders can reach the dashboard over Eagle WiFi.
echo.
pause
