#!/usr/bin/env bash
# Codespaces / Linux / macOS 后端启动脚本
# 用法: 在项目根目录执行 bash scripts/start_backend.sh
#
# 本脚本封装了:
#   1. 自动切换到 backend 目录（main.py 通过 from app.config 导入，需 cwd 在 backend/）
#   2. 通过 python main.py 启动 FastAPI 服务
#   3. 监听 0.0.0.0:8000，Codespaces 会自动转发为公网可访问 URL

set -e  # 任意命令失败立即退出

# 切换到项目根目录（脚本可能在 scripts/ 子目录中被调用）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# 校验 backend 目录存在
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ 未找到 backend 目录: $BACKEND_DIR" >&2
    exit 1
fi

# 校验 main.py 存在
if [ ! -f "$BACKEND_DIR/main.py" ]; then
    echo "❌ 未找到 backend/main.py" >&2
    exit 1
fi

echo "============================================================"
echo "   🚀 启动 宝妈指数后端 (FastAPI)"
echo "   📂 项目根目录: $PROJECT_ROOT"
echo "   📂 工作目录  : $BACKEND_DIR"
echo "============================================================"

# 切换到 backend 目录并启动
cd "$BACKEND_DIR"
# 优先使用 python3，兼容 Codespaces 默认环境
if command -v python3 >/dev/null 2>&1; then
    exec python3 main.py
else
    exec python main.py
fi
