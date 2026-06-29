@echo off
setlocal
set "ROOT=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%ROOT%windows\run.ps1" %*
exit /b %ERRORLEVEL%
