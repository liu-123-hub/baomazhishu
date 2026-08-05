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
echo [1/4] Building frontend...
cd frontend
call npm run build
if errorlevel 1 (
  echo [ERROR] Frontend build failed.
  exit /b 1
)
cd ..
echo   [OK] Frontend built to frontend\dist\
echo.

REM --- Step 2: PyInstaller build ---
echo [2/4] Building backend with PyInstaller...
pyinstaller mom_index.spec --noconfirm --clean
if errorlevel 1 (
  echo [ERROR] PyInstaller build failed.
  exit /b 1
)
echo   [OK] Backend built to dist\MomIndex\
echo.

REM --- Step 3: Download UPX if not present ---
set "UPX_EXE="
if exist "upx\upx.exe" (
  set "UPX_EXE=upx\upx.exe"
) else (
  echo [3/4] Downloading UPX...
  powershell -Command "try { $url='https://github.com/upx/upx/releases/download/v4.2.4/upx-4.2.4-win64.zip'; $tmp=\"$env:TEMP\upx_dl.zip\"; Invoke-WebRequest -Uri $url -OutFile $tmp -UseBasicParsing -TimeoutSec 60; $ext=\"$env:TEMP\upx_dl_ext\"; if (Test-Path $ext) { Remove-Item $ext -Recurse -Force }; Expand-Archive -Path $tmp -DestinationPath $ext -Force; New-Item -ItemType Directory -Path upx -Force | Out-Null; Copy-Item \"$ext\upx-4.2.4-win64\upx.exe\" upx\upx.exe -Force; Remove-Item $tmp -Force; Remove-Item $ext -Recurse -Force; Write-Output 'UPX downloaded' } catch { Write-Output \"UPX download failed: $_\"; exit 1 }"
  if exist "upx\upx.exe" (
    set "UPX_EXE=upx\upx.exe"
  )
)

REM --- Step 4: UPX compress .pyd files (skip all .dll to avoid crashes) ---
if defined UPX_EXE (
  echo [4/4] Compressing .pyd files with UPX ^(skipping .dll and numpy._core^)...
  powershell -Command "$upx='upx\upx.exe'; $internal='dist\MomIndex\_internal'; $targets = Get-ChildItem $internal -Recurse -File -Filter *.pyd | Where-Object { $_.FullName -notmatch 'numpy\\_core' }; foreach ($t in $targets) { try { & $upx $t.FullName --best --quiet 2>&1 | Out-Null } catch {} }; Write-Output \"Compressed $($targets.Count) .pyd files\""
  echo   [OK] UPX compression done
) else (
  echo [4/4] UPX not available, skipping compression
  echo       To enable: download upx.exe to upx\ directory
)
echo.

REM --- Copy run.bat to dist ---
copy run.bat "dist\MomIndex\run.bat" >nul 2>&1

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
