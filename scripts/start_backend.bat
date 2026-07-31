@echo off
REM Windows 后端启动脚本（本地开发用，Codespaces 用 start_backend.sh）
REM 用法: 在项目根目录双击或执行 scripts\start_backend.bat

setlocal enabledelayedexpansion

REM 定位项目根目录（脚本位于 scripts/ 下）
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
set "BACKEND_DIR=%PROJECT_ROOT%\backend"

REM 校验 backend 目录存在
if not exist "%BACKEND_DIR%" (
    echo [X] 未找到 backend 目录: %BACKEND_DIR%
    exit /b 1
)

if not exist "%BACKEND_DIR%\main.py" (
    echo [X] 未找到 backend\main.py
    exit /b 1
)

echo ============================================================
echo    ^_^) 启动 宝妈指数后端 (FastAPI)
echo    项目根目录: %PROJECT_ROOT%
echo    工作目录  : %BACKEND_DIR%
echo ============================================================

REM 切换到 backend 目录并启动
cd /d "%BACKEND_DIR%"
python main.py
