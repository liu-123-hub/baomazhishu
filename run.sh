#!/usr/bin/env bash
# ====================================================================
#  宝妈指数系统一键启动脚本（macOS / Linux）
#  - 自动定位并启动打包后的可执行程序（前端+后端一体化）
#  - 可通过环境变量 MOM_PORT 修改端口，例如：MOM_PORT=8080 ./run.sh
# ====================================================================
set -e
cd "$(dirname "$0")"

# 定位可执行文件：优先同目录（分发包内），其次 dist/MomIndex（构建产物）
EXE=""
if [ -f "./MomIndex" ]; then
  EXE="./MomIndex"
elif [ -f "./dist/MomIndex/MomIndex" ]; then
  EXE="./dist/MomIndex/MomIndex"
elif [ -f "./dist/MomIndex/MomIndex.app/Contents/MacOS/MomIndex" ]; then
  EXE="./dist/MomIndex/MomIndex.app/Contents/MacOS/MomIndex"
fi

if [ -z "$EXE" ]; then
  echo "[错误] 未找到 MomIndex 可执行文件"
  echo "请先执行打包：pyinstaller mom_index.spec --noconfirm"
  echo "或将本脚本与 MomIndex 放在同一目录。"
  exit 1
fi

# 赋予可执行权限（从源码分发包拷贝时可能丢失）
chmod +x "$EXE" 2>/dev/null || true

# 端口配置（默认 8000，可由 MOM_PORT 覆盖）
export PORT="${MOM_PORT:-8000}"

echo "=================================================="
echo "  宝妈指数系统 - 启动中"
echo "  服务端口: $PORT"
echo "  访问地址: http://localhost:$PORT"
echo "  API 文档: http://localhost:$PORT/docs"
echo "  按 Ctrl+C 停止服务"
echo "=================================================="
echo

"$EXE"
