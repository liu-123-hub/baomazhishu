import os
import shutil
import sys
import threading
import webbrowser

from app.config import settings


def _is_frozen() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _copy_seed_data() -> None:
    if not _is_frozen():
        return
    seed_dir = settings.SEED_DATA_DIR
    data_dir = settings.DATA_DIR
    if not seed_dir.is_dir():
        return
    data_dir.mkdir(parents=True, exist_ok=True)
    for fname in os.listdir(str(seed_dir)):
        if fname.endswith('.json'):
            src = seed_dir / fname
            dst = data_dir / fname
            
            if not dst.exists() or (src.stat().st_mtime > dst.stat().st_mtime):
                try:
                    shutil.copy2(str(src), str(dst))
                except Exception:
                    pass


_copy_seed_data()

import uvicorn

from app.main import app  


def _open_browser_when_ready(url: str, delay: float = 2.5) -> None:
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
