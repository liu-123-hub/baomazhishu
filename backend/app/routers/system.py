import sys
from datetime import datetime, timedelta

from fastapi import APIRouter, Query

from ..cache import dashboard_cache, data_cache
from ..auto_collector import auto_collector
from ..config import settings
from ..database import db

router = APIRouter()

_PROJECT_ROOT = str(settings.PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


@router.get("/health")
async def health_check():
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
    await db.add_audit_log(
        username="api_user",
        action="cache_clear",
        endpoint="/api/v1/system/cache/clear",
        status="success",
    )
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


@router.post("/collect/trigger")
async def trigger_collection():
    import asyncio

    status = await auto_collector.get_status()
    if status["status"] == auto_collector.STATUS_RUNNING:
        return {
            "code": 409,
            "message": "采集任务正在运行中，请稍后再试",
            "data": {"status": status},
        }
    await db.add_audit_log(
        username="api_user",
        action="manual_collect_triggered",
        endpoint="/api/v1/system/collect/trigger",
        status="success",
    )
    task = asyncio.create_task(auto_collector.run_with_retry(trigger="manual"))
    task.add_done_callback(_collect_task_done)
    _collect_tasks.add(task)
    return {
        "code": 200,
        "message": "采集任务已启动",
        "data": {
            "triggered_at": datetime.now().isoformat(),
        },
    }


_collect_tasks: set = set()


def _collect_task_done(task):
    """记录异常并从集合移除。"""
    _collect_tasks.discard(task)
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        import logging
        logging.getLogger(__name__).error(f"手动采集任务异常: {exc}", exc_info=exc)


@router.get("/source-health")
async def source_health_check():
    from collectors.source_health_check import run_health_check
    result = await run_health_check()
    return {
        "code": 200,
        "message": "success",
        "data": result,
    }


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(default=50, ge=1, le=500),
    action: str = Query(default=None),
):
    async with db.get_connection() as conn:
        if action:
            cursor = await conn.execute(
                "SELECT * FROM audit_logs WHERE action = ? ORDER BY id DESC LIMIT ?",
                (action, limit),
            )
        else:
            cursor = await conn.execute(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        rows = await cursor.fetchall()
        logs = [dict(r) for r in rows]
    return {
        "code": 200,
        "message": "success",
        "data": logs,
    }
