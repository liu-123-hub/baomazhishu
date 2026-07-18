"""系统管理路由。"""
import sys

from fastapi import APIRouter

from ..cache import dashboard_cache, data_cache
from ..auto_collector import auto_collector
from ..config import settings

router = APIRouter()

_PROJECT_ROOT = str(settings.PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@router.get("/health")
async def health_check():
    from datetime import datetime
    return {
        "code": 200,
        "message": "success",
        "data": {
            "status": "ok",
            "time": datetime.now().isoformat(),
        },
    }


@router.get("/status")
async def system_status():
    dashboard_stats = await dashboard_cache.stats()
    data_stats = await data_cache.stats()

    return {
        "code": 200,
        "message": "success",
        "data": {
            "caches": {
                "dashboard_cache": dashboard_stats,
                "data_cache": data_stats,
            },
        },
    }


@router.post("/cache/clear")
async def clear_cache():
    n1 = await dashboard_cache.clear()
    n2 = await data_cache.clear()
    return {
        "code": 200,
        "message": "缓存已清空",
        "data": {
            "cleared": n1 + n2,
        },
    }


@router.get("/collection-status")
async def collection_status():
    return {
        "code": 200,
        "message": "success",
        "data": await auto_collector.get_status(),
    }


@router.get("/source-health")
async def source_health_check():
    from collectors.source_health_check import run_health_check
    result = await run_health_check()
    return {
        "code": 200,
        "message": "success",
        "data": result,
    }
