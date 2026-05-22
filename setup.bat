@echo off
echo ============================================================
echo  PsyClick Setup
echo ============================================================
echo.

:: ── Python dependencies ──────────────────────────────────────
echo [1/3] Installing Python dependencies...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python is installed and in PATH.
    pause
    exit /b 1
)
echo       Done.

:: ── Node dependencies ─────────────────────────────────────────
echo [2/3] Installing Node.js dependencies...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo ERROR: npm install failed. Make sure Node.js is installed and in PATH.
    cd ..
    pause
    exit /b 1
)
cd ..
echo       Done.

echo.
echo [3/3] Setup complete!
echo.
echo ============================================================
echo  To start (dev mode):  start.bat
echo  To build installer:   build.bat
echo ============================================================
echo.
pause
