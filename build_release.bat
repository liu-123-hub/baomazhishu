@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ====================================================================
REM  MomIndex optimized release build script (Windows)
REM  Steps: frontend build -> PyInstaller -> UPX (.pyd only) -> size report
REM
REM  Prerequisites:
REM    - Node.js + npm (for frontend)
REM    - Python with project deps installed (pip install -r requirements.txt)
REM    - PyInstaller (pip install pyinstaller)
REM  UPX is auto-downloaded if not present.
REM ====================================================================

echo ================================================================
echo   MomIndex Release Build (optimized)
echo ================================================================
echo.

REM --- Step 1: Frontend build ---
echo [1/5] Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
  echo [ERROR] Frontend build failed.
  exit /b 1
)
cd ..
echo   [OK] Frontend built to frontend\dist\
echo.

REM --- Step 2: Verify icon file before build ---
echo [2/5] Verifying icon resources...
if not exist "icon.ico" (
  echo [ERROR] icon.ico not found! Cannot build without program icon.
  exit /b 1
)
if not exist "icon.png" (
  echo [WARNING] icon.png not found, proceeding with .ico only.
) else (
  echo   [OK] icon.ico and icon.png found.
)
echo.

REM --- Step 3: PyInstaller build ---
echo [3/5] Building backend with PyInstaller...
pyinstaller mom_index.spec --noconfirm --clean
if errorlevel 1 (
  echo [ERROR] PyInstaller build failed.
  exit /b 1
)
echo   [OK] Backend built to dist\MomIndex\
echo.

REM --- Verify icon embedded in EXE ---
echo   Verifying icon embedding in MomIndex.exe...
powershell -ExecutionPolicy Bypass -File "%~dp0verify_icon.ps1" -ExePath "%~dp0dist\MomIndex\MomIndex.exe"
echo.

REM --- Step 4: Download UPX if not present ---
set "UPX_EXE="
if exist "upx\upx.exe" (
  set "UPX_EXE=upx\upx.exe"
) else (
  echo [4/5] Downloading UPX...
  powershell -ExecutionPolicy Bypass -File "%~dp0download_upx.ps1"
  if exist "upx\upx.exe" (
    set "UPX_EXE=upx\upx.exe"
  )
)

REM --- Step 5: UPX compress .pyd files (skip all .dll to avoid crashes) ---
if defined UPX_EXE (
  echo [5/5] Compressing .pyd files with UPX ^(skipping .dll and numpy._core^)...
  powershell -ExecutionPolicy Bypass -File "%~dp0compress_pyd.ps1" -UpxExe "%~dp0upx\upx.exe" -InternalDir "%~dp0dist\MomIndex\_internal"
  echo   [OK] UPX compression done
) else (
  echo [5/5] UPX not available, skipping compression
  echo       To enable: download upx.exe to upx\ directory
)
echo.

REM --- Copy run.bat and icon files to dist ---
copy run.bat "dist\MomIndex\run.bat" >nul 2>&1
copy icon.ico "dist\MomIndex\icon.ico" >nul 2>&1
copy icon.png "dist\MomIndex\icon.png" >nul 2>&1
echo   [OK] Copied run.bat, icon.ico, icon.png to dist\MomIndex\

REM --- Copy data directory to dist (运行时 DATA_DIR 指向此目录，确保市场数据/行情数据可用) ---
if not exist "dist\MomIndex\data" mkdir "dist\MomIndex\data"
copy "data\*.json" "dist\MomIndex\data\" >nul 2>&1
echo   [OK] Copied data files to dist\MomIndex\data\


REM --- Final size report ---
echo ================================================================
echo   BUILD COMPLETE
echo ================================================================
powershell -Command "$exe=(Get-Item 'dist\MomIndex\MomIndex.exe').Length; $total=(Get-ChildItem 'dist\MomIndex' -Recurse -File | Measure-Object -Property Length -Sum).Sum; Write-Output ('MomIndex.exe:  {0:N2} MB' -f ($exe/1MB)); Write-Output ('Total package: {0:N2} MB' -f ($total/1MB)); if ($total -lt 100MB) { Write-Output '100MB limit:   PASS' } else { Write-Output '100MB limit:   FAIL' }"
echo.
echo Deliverable: dist\MomIndex\
echo Run:         dist\MomIndex\run.bat
echo ================================================================
endlocal
