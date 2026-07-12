@echo off
:: Usage:
::   BUILD_CLINICAL.bat            -- full build (Python + frontend + package)
::   BUILD_CLINICAL.bat --frontend -- rebuild frontend + repackage only (skip pip + PyInstaller)

set FRONTEND_ONLY=0
if /i "%~1"=="--frontend" set FRONTEND_ONLY=1

echo ============================================================
echo  PsyClick Clinical Edition -- Full Production Build
echo  Clinician-only build. Normative tester portal removed.
echo  CALIBRATED: Fuzzy logic parameters updated with real normative data
echo  Normative baseline: 110-session population (p99-calibrated)
if "%FRONTEND_ONLY%"=="1" echo  MODE: Frontend-only rebuild (skipping Python/PyInstaller)
echo ============================================================
echo.

if "%FRONTEND_ONLY%"=="1" goto :step3

:: ── Step 1: Python dependencies ──────────────────────────────
echo [1/4] Installing Python dependencies...
if not exist requirements.txt (
    echo       SKIP: requirements.txt not found -- Python backend is pre-bundled.
    echo       Using existing dist-python\psyclick_api\ bundle.
    goto :step2_pyinstaller
)
echo       (this may take a few minutes on first run -- you will see progress below)
pip install -r requirements.txt --prefer-binary --no-deps
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python 3.9+ is installed and in PATH.
    pause & exit /b 1
)
echo       Done.

:: ── Step 2: Bundle Python API with PyInstaller ───────────────
:step2_pyinstaller
echo.
echo [2/4] Bundling Python API (PyInstaller)...
if not exist psyclick_api.spec (
    echo       SKIP: psyclick_api.spec not found -- using existing pre-bundled binary.
    if exist dist-python\psyclick_api\psyclick_api.exe (
        echo       Found: dist-python\psyclick_api\psyclick_api.exe  [OK]
        copy config.json dist-python\psyclick_api\config.json >nul
    ) else (
        echo ERROR: No pre-bundled psyclick_api.exe found in dist-python\psyclick_api\
        echo        Please obtain the compiled backend or add psyclick_api.spec to rebuild.
        pause & exit /b 1
    )
    goto :step3
)
echo       This may take 2-3 minutes on first run...
pyinstaller psyclick_api.spec --noconfirm --distpath dist-python
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller failed. Install it with: pip install pyinstaller
    pause & exit /b 1
)
echo       Copying config.json to dist-python...
copy config.json dist-python\psyclick_api\config.json
echo       Done.

:: ── Step 3: Build React frontend ─────────────────────────────
:step3
echo.
echo [3/4] Building React frontend (PsyClick Clinical Edition)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo ERROR: npm install failed. Make sure Node.js 18+ is installed.
    cd .. & pause & exit /b 1
)
call npm run build
if %errorlevel% neq 0 (
    echo ERROR: npm build failed.
    cd .. & pause & exit /b 1
)
echo       Done.

:: ── Step 4: Package with electron-builder ────────────────────
echo.
echo [4/4] Creating Windows installer (PsyClick Clinical Edition)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$names=@('PsyClick Clinical Edition','psyclick_api','electron','app-builder'); foreach($n in $names){Get-Process -Name $n -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue}; Start-Sleep -Seconds 2; $p='dist-electron-clinical\win-unpacked'; if(Test-Path $p){for($i=1;$i -le 5;$i++){try{Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop; break}catch{Write-Host ('Cleanup retry '+$i+': '+$_.Exception.Message); Start-Sleep -Seconds 3}}}"
set CSC_IDENTITY_AUTO_DISCOVERY=false
set WIN_CSC_LINK=
call npx electron-builder
if %errorlevel% neq 0 (
    echo ERROR: electron-builder failed.
    cd .. & pause & exit /b 1
)
cd ..

echo.
echo ============================================================
echo  BUILD COMPLETE -- PsyClick Clinical Edition
echo ============================================================
echo.
echo  Installer : frontend\dist-electron-clinical\PsyClick Clinical Edition Setup.exe
echo  Portable  : frontend\dist-electron-clinical\PsyClick Clinical Edition*.exe
echo.
echo  CALIBRATION UPDATES (May 10, 2026):
echo  - Fuzzy logic parameters calibrated to real normative data (110 sessions)
echo  - t2_ratio range: 0.0 to 7.00 (p99 = 6.9975)
echo  - PSI range: 0.0 to 39.10 (p99 = 39.1050)
echo  - PAI range: 0.0 to 107.83 (p99 = 107.8280)
echo  - RED/AMBER/GREEN flags now achievable (target: 5/15/80 distribution)
echo  - Database credentials removed (uses environment config only)
echo  - EWMA baseline, T^2 computation, feature extraction unchanged
echo.
echo  Edition-specific features:
echo  - Normative tester portal REMOVED (clinicians only)
echo  - PSI: Psychomotor Slowing Index
echo  - PAI: Psychomotor Agitation Index
echo  - Normative baseline always available
echo  - Population comparison auto-loads on every session report
echo  - App ID: com.psyclick.clinical (separate from com.psyclick.app)
echo.
pause
