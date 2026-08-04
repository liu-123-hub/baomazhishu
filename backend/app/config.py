"""应用配置，支持环境变量覆盖。板块配置从 analyzer 统一导入。

打包模式（PyInstaller frozen）下的路径策略：
- RESOURCE_DIR: 只读打包资源目录（sys._MEIPASS），存放前端静态文件与种子数据
- PROJECT_ROOT:  可写运行目录（可执行文件所在目录），存放运行时生成的 data/logs/db
- 开发模式下两者均为项目根目录
"""
import os
import shutil
import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


def _is_frozen() -> bool:
    """是否运行于 PyInstaller 打包环境中。"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


# 资源目录（只读）：打包后指向 _MEIPASS；开发模式指向项目根
RESOURCE_DIR: Path = Path(sys._MEIPASS) if _is_frozen() else Path(__file__).resolve().parent.parent.parent

# 项目根（可写）：打包后指向可执行文件所在目录；开发模式指向项目根
PROJECT_ROOT_PATH: Path = Path(sys.executable).resolve().parent if _is_frozen() else Path(__file__).resolve().parent.parent.parent

# 开发模式下需要将项目根加入 sys.path 以支持 analyzer/collectors 顶层导入；
# 打包后 PyInstaller 自动处理 _MEIPASS，无需手动添加
if not _is_frozen():
    if str(RESOURCE_DIR) not in sys.path:
        sys.path.insert(0, str(RESOURCE_DIR))

from analyzer.index_calculator import (
    SECTOR_NAMES as _SECTOR_NAMES,
    SECTOR_CATEGORIES as _SECTOR_CATEGORIES,
    SECTOR_META as _SECTOR_META,
    INDUSTRY_SECTORS as _INDUSTRY_SECTORS,
    CONCEPT_SECTORS as _CONCEPT_SECTORS,
    TIER_COLORS as _TIER_COLORS,
    get_sector_type,
    get_sector_tier,
    get_related_sectors,
)


class Settings(BaseSettings):

    PROJECT_NAME: str = "实时数据大屏系统"
    API_V1_PREFIX: str = "/api"
    DEBUG: bool = False

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://app.momindex.local",
        "https://app.momindex.local",
        "capacitor://localhost",
        "http://localhost",
        "http://10.0.2.2",
        "http://10.0.2.2:8000",
    ]

    CORS_ALLOW_LOCALHOST_REGEX: bool = True

    # 可写运行目录（打包后为可执行文件所在目录）
    PROJECT_ROOT: Path = PROJECT_ROOT_PATH
    # 运行时数据目录（可写，存放 collectors 产出的 JSON 与数据库）
    DATA_DIR: Path = PROJECT_ROOT_PATH / "data"
    # 后端目录（用于日志输出；打包后为可执行文件所在目录下的 backend）
    BACKEND_DIR: Path = PROJECT_ROOT_PATH / "backend"
    DB_PATH: Path = PROJECT_ROOT_PATH / "backend" / "dashboard.db"
    # 前端静态资源目录（只读）：打包后指向 _MEIPASS/frontend_dist；开发模式指向 frontend/dist
    STATIC_DIR: Path = RESOURCE_DIR / "frontend_dist" if _is_frozen() else PROJECT_ROOT_PATH / "frontend" / "dist"
    # 打包内种子数据目录（只读）
    SEED_DATA_DIR: Path = RESOURCE_DIR / "data" if _is_frozen() else PROJECT_ROOT_PATH / "data"

    CACHE_TTL: int = 300
    CACHE_MAX_SIZE: int = 500
    DASHBOARD_CACHE_TTL: int = 30
    DASHBOARD_CACHE_MAX_SIZE: int = 100

    WS_HEARTBEAT_INTERVAL: int = 30
    WS_BROADCAST_INTERVAL: int = 5

    COLLECTOR_TIMEOUT: int = 30
    COLLECTOR_RETRY_TIMES: int = 3
    PLAYWRIGHT_HEADLESS: bool = True
    AUTO_COLLECT_INTERVAL: int = 1800
    COLLECTOR_RUN_DEADLINE: int = 1500
    WATCHDOG_CHECK_INTERVAL: int = 300
    WATCHDOG_GRACE: int = 60

    SECTOR_CATEGORIES: list = _SECTOR_CATEGORIES
    SECTOR_NAMES: dict = _SECTOR_NAMES
    SECTOR_META: dict = _SECTOR_META
    INDUSTRY_SECTORS: list = _INDUSTRY_SECTORS
    CONCEPT_SECTORS: list = _CONCEPT_SECTORS
    TIER_COLORS: dict = _TIER_COLORS

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.BACKEND_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_seed_data() -> None:
    """打包模式下首次运行时，将只读资源内的种子数据 JSON 拷贝到可写数据目录。

    开发模式下数据目录即源数据目录，无需拷贝。
    """
    if not _is_frozen():
        return
    src = settings.SEED_DATA_DIR
    if not src.is_dir():
        return
    for json_file in src.glob("*.json"):
        dst = settings.DATA_DIR / json_file.name
        if not dst.exists():
            try:
                shutil.copy2(json_file, dst)
            except OSError:
                pass


_ensure_seed_data()
