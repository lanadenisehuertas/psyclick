@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0auto_rebuild_deploy.ps1" %*
if %errorlevel% neq 0 (
    echo.
    echo Automatic rebuild/deploy failed. See build_log.txt for details.
    exit /b %errorlevel%
)
echo.
echo Automatic rebuild/deploy completed successfully.
