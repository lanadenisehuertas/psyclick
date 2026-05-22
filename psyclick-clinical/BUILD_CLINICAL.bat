@echo off
echo ============================================================
echo  PsyClick Clinical Edition -- Full Production Build
echo  Clinician-only build. Normative tester portal removed.
echo  CALIBRATED: Fuzzy logic parameters updated with real normative data
echo  Normative baseline: 110-session population (p99-calibrated)
echo ============================================================
echo.

:: ── Step 1: Python dependencies ──────────────────────────────
echo [1/4] Installing Python dependencies...
echo       (this may take a few minutes on first run -- you will see progress below)
pip install -r requirements.txt --prefer-binary --no-deps
if %errorlevel% neq 0 (
    echo ERROR: pip install failed. Make sure Python 3.9+ is installed and in PATH.
    pause & exit /b 1
)
echo       Done.

:: ── Step 2: Bundle Python API with PyInstaller ───────────────
echo.
echo [2/4] Bundling Python API (PyInstaller)...
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
