Set oShell = CreateObject("Shell.Application")
oShell.ShellExecute "powershell.exe", "-NoProfile -Command New-NetFirewallRule -DisplayName 'TIMWOOD FMO Dashboard' -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow -Profile Any", "", "runas", 1
