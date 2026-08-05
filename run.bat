@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ================================================
echo   宝妈指数系统 (MomIndex) 启动中...
echo ================================================
echo.
echo   访问地址: http://localhost:8000
echo   按 Ctrl+C 停止服务
echo.
start /b "" "MomIndex.exe"
echo   服务已启动，浏览器将自动打开...
echo.
pause
