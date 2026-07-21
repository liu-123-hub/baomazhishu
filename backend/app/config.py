"""应用配置，支持环境变量覆盖。"""
import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings


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
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    BACKEND_DIR: Path = PROJECT_ROOT / "backend"
    DB_PATH: Path = BACKEND_DIR / "dashboard.db"

    CACHE_TTL: int = 300
    CACHE_MAX_SIZE: int = 500

    WS_HEARTBEAT_INTERVAL: int = 30
    WS_BROADCAST_INTERVAL: int = 5

    COLLECTOR_TIMEOUT: int = 30
    COLLECTOR_RETRY_TIMES: int = 3
    PLAYWRIGHT_HEADLESS: bool = True
    AUTO_COLLECT_INTERVAL: int = 1800

    SECTOR_CATEGORIES: list = [
        {
            "code": "finance",
            "name": "大金融",
            "children": ["bank", "securities", "insurance"]
        },
        {
            "code": "consumption",
            "name": "大消费",
            "children": ["baijiu", "food", "medicine", "appliance", "tourism", "biotech", "consumer"]
        },
        {
            "code": "technology",
            "name": "大科技",
            "children": ["electronics", "computer", "communication", "media", "cpo", "semiconductor"]
        },
        {
            "code": "cyclical",
            "name": "大周期",
            "children": ["nonferrous", "coal", "chemical", "steel", "realestate", "infrastructure", "newenergy"]
        },
        {
            "code": "others",
            "name": "其他",
            "children": ["nasdaq", "gold"]
        }
    ]

    SECTOR_NAMES: dict = {
        "bank": "银行",
        "securities": "券商",
        "insurance": "保险",
        "baijiu": "白酒",
        "food": "食品",
        "medicine": "医药",
        "appliance": "家电",
        "tourism": "文旅",
        "biotech": "创新药",
        "consumer": "消费",
        "electronics": "电子",
        "computer": "计算机",
        "communication": "通信",
        "media": "传媒",
        "cpo": "CPO通信",
        "semiconductor": "半导体",
        "nonferrous": "有色",
        "coal": "煤炭",
        "chemical": "化工",
        "steel": "钢铁",
        "realestate": "地产",
        "infrastructure": "基建",
        "newenergy": "新能源",
        "nasdaq": "纳斯达克",
        "gold": "黄金"
    }

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.BACKEND_DIR.mkdir(parents=True, exist_ok=True)
