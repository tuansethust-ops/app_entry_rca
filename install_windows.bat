@echo off
setlocal
set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%windows\install.ps1" %*
exit /b %ERRORLEVEL%
