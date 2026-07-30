"""应用配置，支持环境变量覆盖。

板块分类 v2.0：从 analyzer.index_calculator 统一导入 SECTOR_NAMES、SECTOR_CATEGORIES、
SECTOR_META 等配置，确保前后端和采集器使用唯一真值来源。
"""
import os
import sys
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings

# 从 analyzer 导入板块配置作为唯一真值来源，避免多处维护
# config.py 在后端启动时最先加载，需自行注入根目录到 sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

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

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    BACKEND_DIR: Path = PROJECT_ROOT / "backend"
    DB_PATH: Path = BACKEND_DIR / "dashboard.db"

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
    # 必须 < AUTO_COLLECT_INTERVAL，防止单次卡死导致周期无限堆积
    COLLECTOR_RUN_DEADLINE: int = 1500
    # 看门狗检查间隔与告警宽限期：检测漏触发/卡死的采集周期
    WATCHDOG_CHECK_INTERVAL: int = 300
    WATCHDOG_GRACE: int = 60

    # 板块分类 v2.0：从核心定义统一导入，按投资风格梯队组织
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
