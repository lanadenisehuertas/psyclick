@echo off
setlocal
cd /d "%~dp0"
set "PSYCLICK_SECURE_HOME=%APPDATA%\PsyClickSecure"
if not exist "%PSYCLICK_SECURE_HOME%" mkdir "%PSYCLICK_SECURE_HOME%"
start "PsyClick Secure API" cmd /k "python api_server.py"
cd frontend
call npm run dev
