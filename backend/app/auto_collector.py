"""自动数据采集模块，后台执行 pipeline.py 并维护采集状态。"""
import asyncio
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from .cache import dashboard_cache
from .config import settings
from .database import db
from .websocket import manager

logger = logging.getLogger(__name__)

_PROJECT_ROOT = str(settings.PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


class AutoCollector:
    """自动数据采集器，支持启动全量采集和定时采集。"""

    STATUS_IDLE = "idle"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    def __init__(self):
        self._status: Dict[str, Any] = {
            "status": self.STATUS_IDLE,
            "progress": 0,
            "step": "等待启动",
            "message": "等待启动",
            "started_at": None,
            "finished_at": None,
            "retry_count": 0,
            "max_retries": settings.COLLECTOR_RETRY_TIMES,
            "error": None,
            "sources": {},
            "trigger": "idle",
            "last_success_at": None,
            "next_run_at": None,
            "interval_seconds": settings.AUTO_COLLECT_INTERVAL,
            "preflight": [],
            "provenance": {},
        }
        self._lock = asyncio.Lock()
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="auto_collect_")
        self._periodic_task: Optional[asyncio.Task] = None
        self._startup_task: Optional[asyncio.Task] = None

    async def get_status(self) -> Dict[str, Any]:
        async with self._lock:
            return dict(self._status)

    async def _update_status(self, **kwargs):
        async with self._lock:
            self._status.update(kwargs)
        await self._broadcast_status()

    async def _broadcast_status(self):
        try:
            await manager.broadcast({
                "type": "collection_status",
                "data": await self.get_status(),
                "timestamp": datetime.now().isoformat(),
            })
        except Exception:
            pass

    def _run_pipeline_sync(self) -> Dict[str, Any]:
        import sys
        project_root = str(settings.PROJECT_ROOT)
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        from pipeline import run_pipeline
        return run_pipeline()

    async def _sync_latest_to_db(self, dashboard: Dict[str, Any]):
        latest = dashboard.get("latest") or {}
        sectors = latest.get("sectors") or {}
        record_date = latest.get("date")
        if not record_date or not sectors:
            logger.warning("pipeline 返回数据中无最新板块记录，跳过数据库同步")
            return

        provenance = dashboard.get("data_provenance") or {}
        has_user_discussion = provenance.get("has_user_discussion", True)
        if not has_user_discussion:
            logger.warning(
                "所有用户讨论源（股吧/小红书/雪球）均返回 0 条记录，"
                "本次采集数据质量降级，跳过数据库同步以保留上次优质数据"
            )
            # 计算数据指纹，便于在审计日志中追溯本次降级采集批次
            fingerprints = provenance.get("fingerprints", []) or []
            import hashlib
            import json as _json
            fp_str = _json.dumps(
                [{"s": f.get("source_name"), "r": f.get("record_count")} for f in fingerprints],
                sort_keys=True,
            )
            degraded_fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()[:16] if fingerprints else ""
            await db.add_audit_log(
                username="system",
                action="data_sync_skipped",
                endpoint="auto_collector",
                status="degraded",
                duration_ms=0,
                data_fingerprint=degraded_fingerprint,
                sector_count=len(sectors),
                detail="所有用户讨论源（股吧/小红书/雪球）均返回 0 条记录，仅新闻源有数据",
            )
            return

        fingerprints = provenance.get("fingerprints", [])
        source_fingerprint = ""
        if fingerprints:
            import hashlib
            import json
            fp_str = json.dumps([{"s": f.get("source_name"), "r": f.get("record_count")} for f in fingerprints], sort_keys=True)
            source_fingerprint = hashlib.sha256(fp_str.encode()).hexdigest()[:16]

        all_sources_passed = all(f.get("passed", False) for f in fingerprints) if fingerprints else True
        synced_count = 0
        skipped_count = 0
        failed_sectors: list = []

        for code, data in sectors.items():
            if code not in settings.SECTOR_NAMES:
                continue
            details = data.get("details") or {}
            total_posts = details.get("total_posts", 0)
            if total_posts == 0:
                logger.info(f"板块 [{code}] 无采集数据(total_posts=0)，跳过数据库写入")
                skipped_count += 1
                continue
            try:
                await db.insert_sector_index({
                    "sector_code": code,
                    "sector_name": settings.SECTOR_NAMES.get(code, code),
                    "index_value": data.get("index", 0),
                    "buy_index": details.get("mom_buy_index", 0),
                    "sell_index": details.get("mom_sell_index", 0),
                    "newbie_ratio": details.get("newbie_ratio", 0),
                    "total_posts": total_posts,
                    "record_date": record_date,
                    "data_source": "pipeline_multi_source",
                    "data_fingerprint": source_fingerprint,
                    "source_passed": all_sources_passed,
                    "user_discussion_present": has_user_discussion,
                })
                synced_count += 1
            except Exception as e:
                logger.error(f"同步板块 [{code}] 到数据库失败: {e}")
                skipped_count += 1
                failed_sectors.append(code)

        await db.add_audit_log(
            username="system",
            action="data_sync_complete",
            endpoint="auto_collector",
            status="success" if not failed_sectors else "partial",
            duration_ms=0,
            data_fingerprint=source_fingerprint,
            sector_count=synced_count,
            detail=(
                f"写入 {synced_count} 个板块，跳过 {skipped_count} 个"
                + (f"，失败板块: {','.join(failed_sectors)}" if failed_sectors else "")
            ),
        )
        logger.info(f"数据库同步完成: {synced_count}个板块写入, {skipped_count}个跳过")

    async def run_once(self, trigger: str = "scheduled"):
        """执行一次完整的自动采集流程。"""
        await self._update_status(
            status=self.STATUS_RUNNING,
            progress=5,
            step="数据源预检",
            message="正在执行数据源连通性预检...",
            started_at=datetime.now().isoformat(),
            finished_at=None,
            error=None,
            sources={},
            trigger=trigger,
        )

        preflight = []
        try:
            from collectors.source_health_check import run_health_check
            health_result = await run_health_check()
            preflight = health_result.get("details", [])
            summary = health_result.get("summary", {})
            reachable = summary.get("reachable", 0)
            total = summary.get("total", 0)
            await self._update_status(
                progress=15,
                step="数据源预检完成",
                message=f"数据源预检完成：{reachable}/{total} 可达",
            )
        except Exception as e:
            logger.warning(f"数据源连通性预检失败（不阻断采集）: {e}")
            await self._update_status(
                progress=15,
                step="数据源预检异常",
                message=f"数据源预检异常（继续尝试采集）: {str(e)[:80]}",
            )

        try:
            await self._update_status(progress=20, step="执行采集", message="正在从多个真实数据源采集市场数据，请稍候...")
            loop = asyncio.get_event_loop()
            dashboard = await loop.run_in_executor(self._executor, self._run_pipeline_sync)

            if not dashboard or not isinstance(dashboard, dict):
                raise RuntimeError("采集返回数据格式异常")

            await self._update_status(progress=80, step="同步数据库", message="正在将最新数据同步到本地数据库...")
            await self._sync_latest_to_db(dashboard)

            await dashboard_cache.clear()

            record_count = dashboard.get("record_count", 0)
            total_posts = sum(
                (s.get("details") or {}).get("total_posts", 0)
                for s in (dashboard.get("latest") or {}).get("sectors", {}).values()
            )
            provenance = dashboard.get("data_provenance", {})
            now_iso = datetime.now().isoformat()
            await self._update_status(
                status=self.STATUS_SUCCESS,
                progress=100,
                step="完成",
                message=f"数据更新成功：{record_count} 天历史，今日共 {total_posts} 条真实数据",
                finished_at=now_iso,
                last_success_at=now_iso,
                retry_count=0,
                error=None,
                sources=dashboard.get("data_sources", {}),
                preflight=preflight,
                provenance=provenance,
            )
            logger.info(f"自动数据采集完成 (触发: {trigger})")
        except Exception as e:
            logger.exception("自动数据采集失败")
            await self._update_status(
                status=self.STATUS_FAILED,
                progress=0,
                step="失败",
                message=f"数据更新失败: {str(e)}",
                finished_at=datetime.now().isoformat(),
                error=str(e),
                preflight=preflight,
            )

    async def run_with_retry(self, trigger: str = "scheduled"):
        """带重试机制的采集入口。"""
        max_retries = (await self.get_status())["max_retries"]
        for attempt in range(max_retries + 1):
            await self._update_status(retry_count=attempt)
            await self.run_once(trigger=trigger)
            status = await self.get_status()
            if status["status"] == self.STATUS_SUCCESS:
                break
            if attempt < max_retries:
                wait = 5 * (attempt + 1)
                logger.warning(f"自动采集失败，{wait} 秒后重试（第 {attempt + 1}/{max_retries} 次）...")
                await self._update_status(message=f"采集失败，{wait} 秒后重试 ({attempt + 1}/{max_retries})")
                await asyncio.sleep(wait)

    async def _periodic_loop(self):
        """定时采集循环，每隔 AUTO_COLLECT_INTERVAL 秒执行一次。"""
        while True:
            status = await self.get_status()
            if status["status"] in (self.STATUS_SUCCESS, self.STATUS_FAILED):
                break
            await asyncio.sleep(2)

        interval = settings.AUTO_COLLECT_INTERVAL
        logger.info(f"定时采集循环已启动，间隔 {interval} 秒")

        while True:
            next_run = datetime.now() + timedelta(seconds=interval)
            await self._update_status(next_run_at=next_run.isoformat())

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                logger.info("定时采集循环已停止")
                raise

            logger.info("定时采集触发，开始执行增量+全量数据拉取...")
            await self.run_with_retry(trigger="scheduled")

    async def start(self):
        self._startup_task = asyncio.create_task(self.run_with_retry(trigger="startup"))
        self._periodic_task = asyncio.create_task(self._periodic_loop())

    async def close(self):
        if self._periodic_task and not self._periodic_task.done():
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
        if self._startup_task and not self._startup_task.done():
            self._startup_task.cancel()
            try:
                await self._startup_task
            except asyncio.CancelledError:
                pass
        self._executor.shutdown(wait=False)


auto_collector = AutoCollector()
