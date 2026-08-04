"""生产环境启动入口：PyInstaller 打包主入口，开发模式亦可运行。

与 backend/main.py 的区别：
- 关闭 reload（生产无需热重载，且 reload 在 frozen 模式下不可用）
- 直接以 app 实例启动 uvicorn，避免字符串导入在打包后失效
- 打包模式下服务就绪后自动打开浏览器

开发运行：cd backend && python run_prod.py
打包后：双击运行可执行文件，或通过 run.bat / run.sh 启动
"""
import sys
import threading
import webbrowser

import uvicorn

from app.config import settings
from app.main import app  # 直接导入已构造好的 app 实例


def _is_frozen() -> bool:
    """是否运行于 PyInstaller 打包环境中。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _open_browser_when_ready(url: str, delay: float = 2.5) -> None:
    """服务就绪后延迟打开浏览器（仅打包模式，避免干扰开发）。"""
    def _open():
        import time
        time.sleep(delay)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    if _is_frozen():
        threading.Thread(target=_open, daemon=True).start()


if __name__ == "__main__":
    access_url = f"http://localhost:{settings.PORT}"
    _open_browser_when_ready(access_url)
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        workers=1,
        log_level="info",
        access_log=False,
    )
