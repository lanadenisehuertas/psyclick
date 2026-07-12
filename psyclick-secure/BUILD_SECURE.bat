@echo off
setlocal
cd /d "%~dp0"
echo Building PsyClick Secure backend and frontend...
if not exist .venv\Scripts\python.exe (
  echo Create a virtual environment and install requirements.txt first.
  exit /b 1
)
rem Build backend from the spec into dist-python\psyclick_api so the path and name
rem match what Electron loads (resources\psyclick_api\psyclick_api.exe).
.venv\Scripts\python.exe -m PyInstaller psyclick_api.spec --noconfirm --clean --distpath dist-python
if errorlevel 1 exit /b 1
echo Backend built: dist-python\psyclick_api\psyclick_api.exe
cd frontend
call npm.cmd run build
if errorlevel 1 exit /b 1
echo Secure build complete.
echo Backend  -^> psyclick-secure\dist-python\psyclick_api\psyclick_api.exe
echo Frontend -^> psyclick-secure\frontend\dist\
echo Installer: cd frontend ^&^& npm run dist:installer
