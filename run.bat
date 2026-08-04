@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

REM ====================================================================
REM  MomIndex one-click launcher (Windows)
REM  - Locates and starts the packaged executable (frontend + backend)
REM  - Override port via: set MOM_PORT=8080 && run.bat
REM ====================================================================

REM Locate executable: prefer same dir (distribution), then dist\MomIndex (build output)
set "EXE="
if exist "MomIndex.exe" set "EXE=MomIndex.exe"
if not defined EXE if exist "dist\MomIndex\MomIndex.exe" set "EXE=dist\MomIndex\MomIndex.exe"

if not defined EXE (
  echo [ERROR] MomIndex.exe not found.
  echo Build first: pyinstaller mom_index.spec --noconfirm
  echo Or place this script next to MomIndex.exe.
  pause
  exit /b 1
)

REM Port config (default 8000, overridable by MOM_PORT)
set "PORT=8000"
if defined MOM_PORT set "PORT=%MOM_PORT%"

echo ==================================================
echo   MomIndex - starting
echo   service port: %PORT%
echo   web URL:       http://localhost:%PORT%
echo   API docs:      http://localhost:%PORT%/docs
echo   press Ctrl+C to stop
echo ==================================================
echo.

set "PORT=%PORT%"
"%EXE%"
endlocal
