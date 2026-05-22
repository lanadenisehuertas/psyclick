@echo off
echo ============================================================
echo  PsyClick - Starting...
echo ============================================================
echo.
echo This will launch the API server + React UI + Electron window.
echo.
cd "%~dp0frontend"
call npm run start
cd "%~dp0"
