"""自动数据采集模块，后台执行 pipeline.py 并维护采集状态。"""
import asyncio
import logging
import sys
import time
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
        # _lock 保护 _status 读写一致性，避免广播与周期任务并发写冲突
        self._lock = asyncio.Lock()
        # max_workers=1 保证采集串行执行，避免多实例并发导致资源耗尽
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="auto_collect_")
        self._periodic_task: Optional[asyncio.Task] = None
        self._startup_task: Optional[asyncio.Task] = None
        self._watchdog_task: Optional[asyncio.Task] = None
        # 进程启动时刻，用于看门狗判定"自启动以来从未成功运行过"的漏触发场景
        self._process_start_time = time.monotonic()

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
        sync_start_time = time.monotonic()
        latest = dashboard.get("latest") or {}
        sectors = latest.get("sectors") or {}
        record_date = latest.get("date")
        if not record_date or not sectors:
            logger.warning("pipeline 返回数据中无最新板块记录，跳过数据库同步")
            return

        provenance = dashboard.get("data_provenance") or {}
        has_user_discussion = provenance.get("has_user_discussion", True)
        # 所有用户讨论源均返回 0 条时，本次采集质量降级；
        # 跳过 DB 同步以保留上次优质数据，仅写审计日志留痕
        if not has_user_discussion:
            logger.warning(
                "所有用户讨论源（股吧/小红书/雪球）均返回 0 条记录，"
                "本次采集数据质量降级，跳过数据库同步以保留上次优质数据"
            )
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
                duration_ms=int((time.monotonic() - sync_start_time) * 1000),
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

        is_real_data = provenance.get("is_real_data", False)
        passed_sources = [f for f in fingerprints if f.get("passed")]
        all_sources_passed = is_real_data and len(passed_sources) > 0
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
            duration_ms=int((time.monotonic() - sync_start_time) * 1000),
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
        run_start_time = time.monotonic()
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
            # 设置显式 deadline，避免单个卡死的网络请求让后续周期无限堆积；
            # 超时后放弃当前运行并重置执行器，使下一个周期能立即开始
            deadline = settings.COLLECTOR_RUN_DEADLINE
            try:
                dashboard = await asyncio.wait_for(
                    loop.run_in_executor(self._executor, self._run_pipeline_sync),
                    timeout=deadline,
                )
            except asyncio.TimeoutError:
                # 重置执行器：旧的单工作线程已被卡死，若不重建则后续 run_in_executor
                # 会排在卡死线程之后无限等待，导致周期全部失效
                self._executor.shutdown(wait=False)
                self._executor = ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="auto_collect_"
                )
                timeout_duration_ms = int((time.monotonic() - run_start_time) * 1000)
                logger.error(
                    f"采集超时 (触发={trigger} | 状态=timeout | "
                    f"耗时={timeout_duration_ms}ms | deadline={deadline}s) — "
                    f"已放弃当前运行并重置执行器，下一周期将立即就绪"
                )
                raise RuntimeError(f"采集超时：超过 {deadline} 秒未完成，已重置执行器")

            if not dashboard or not isinstance(dashboard, dict):
                raise RuntimeError("采集返回数据格式异常")

            # 数据合法性校验门：仅当校验通过才覆盖本地数据，避免无效数据污染
            from collectors.data_validation import validate_dashboard_for_sync
            is_valid, validation_issues = validate_dashboard_for_sync(dashboard)
            if not is_valid:
                issue_summary = "; ".join(validation_issues)
                rejected_duration_ms = int((time.monotonic() - run_start_time) * 1000)
                logger.warning(
                    f"数据更新被拒 (触发={trigger} | 状态=rejected | "
                    f"耗时={rejected_duration_ms}ms | 原因={issue_summary})"
                )
                await self._update_status(
                    progress=80,
                    step="数据校验未通过",
                    message=f"数据合法性校验未通过，已拒绝覆盖本地数据: {issue_summary[:120]}",
                )
                await db.add_audit_log(
                    username="system",
                    action="data_sync_rejected",
                    endpoint="auto_collector",
                    status="rejected",
                    duration_ms=rejected_duration_ms,
                    detail=f"数据合法性校验未通过: {issue_summary}",
                )
                raise RuntimeError(f"数据合法性校验未通过: {issue_summary}")

            await self._update_status(progress=80, step="同步数据库", message="正在将最新数据同步到本地数据库...")
            await self._sync_latest_to_db(dashboard)

            # 采集成功后清空缓存，确保下次读取是最新数据
            await dashboard_cache.clear()

            record_count = dashboard.get("record_count", 0)
            total_posts = sum(
                (s.get("details") or {}).get("total_posts", 0)
                for s in (dashboard.get("latest") or {}).get("sectors", {}).values()
            )
            provenance = dashboard.get("data_provenance", {})
            now_iso = datetime.now().isoformat()
            success_duration_ms = int((time.monotonic() - run_start_time) * 1000)
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
            logger.info(
                f"数据更新成功 (触发={trigger} | 状态=success | "
                f"耗时={success_duration_ms}ms | 历史天数={record_count} | "
                f"今日数据量={total_posts}条 | is_real_data={provenance.get('is_real_data', False)})"
            )
        except Exception as e:
            failed_duration_ms = int((time.monotonic() - run_start_time) * 1000)
            logger.exception(
                f"数据更新失败 (触发={trigger} | 状态=failed | "
                f"耗时={failed_duration_ms}ms | 错误={e})"
            )
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
        """定时采集循环，异常不中断定时器。"""
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
            try:
                await self.run_with_retry(trigger="scheduled")
            except asyncio.CancelledError:
                logger.info("定时采集循环已停止")
                raise
            except Exception as e:
                logger.exception(
                    f"定时采集周期发生未预期异常，已记录日志，定时器将继续运行等待下个周期: {e}"
                )

    async def _watchdog_loop(self):
        """看门狗循环：检测漏触发/卡死的采集周期。

        检测两类静默故障：
        1. missed-run：自启动以来或在一个完整周期+deadline+宽限期之后，仍无成功运行
        2. stuck-run：当前状态为 RUNNING 但已远超 deadline，说明 deadline 机制本身
           被绕过（例如事件循环阻塞），需人工介入
        """
        check_interval = settings.WATCHDOG_CHECK_INTERVAL
        interval = settings.AUTO_COLLECT_INTERVAL
        deadline = settings.COLLECTOR_RUN_DEADLINE
        grace = settings.WATCHDOG_GRACE
        # 漏触发阈值 = 一个周期 + 一次最长运行 + 宽限期
        missed_threshold = interval + deadline + grace
        # 卡死阈值 = 单次最长运行 + 宽限期
        stuck_threshold = deadline + grace

        logger.info(
            f"看门狗已启动 (检查间隔={check_interval}s | "
            f"漏触发阈值={missed_threshold}s | 卡死阈值={stuck_threshold}s)"
        )

        while True:
            try:
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                logger.info("看门狗循环已停止")
                raise

            try:
                status = await self.get_status()
                now_mono = time.monotonic()

                # 检测 1：stuck-run（当前运行卡死）
                started_at_iso = status.get("started_at")
                if status.get("status") == self.STATUS_RUNNING and started_at_iso:
                    try:
                        started_dt = datetime.fromisoformat(started_at_iso)
                        started_mono = now_mono - (datetime.now() - started_dt).total_seconds()
                        running_for = now_mono - started_mono
                        if running_for > stuck_threshold:
                            logger.error(
                                f"[看门狗] 卡死告警: 当前采集运行已持续 {int(running_for)}s，"
                                f"超过卡死阈值 {stuck_threshold}s (deadline={deadline}s + grace={grace}s)，"
                                f"started_at={started_at_iso} — 可能事件循环阻塞或 deadline 失效，需人工介入"
                            )
                    except (ValueError, TypeError):
                        pass

                # 检测 2：missed-run（漏触发/长期无成功）
                last_success_iso = status.get("last_success_at")
                if last_success_iso:
                    try:
                        last_success_dt = datetime.fromisoformat(last_success_iso)
                        last_success_mono = now_mono - (datetime.now() - last_success_dt).total_seconds()
                        since_success = now_mono - last_success_mono
                        if since_success > missed_threshold:
                            logger.error(
                                f"[看门狗] 漏触发告警: 距上次成功采集已 {int(since_success)}s，"
                                f"超过漏触发阈值 {missed_threshold}s "
                                f"(interval={interval}s + deadline={deadline}s + grace={grace}s)，"
                                f"last_success_at={last_success_iso} — 定时器可能已停止，需人工介入"
                            )
                    except (ValueError, TypeError):
                        pass
                else:
                    # 自启动以来从未成功过：检查进程运行时长是否超过阈值
                    uptime = now_mono - self._process_start_time
                    if uptime > missed_threshold:
                        logger.error(
                            f"[看门狗] 漏触发告警: 进程已运行 {int(uptime)}s 但从未成功采集过，"
                            f"超过漏触发阈值 {missed_threshold}s — 启动采集可能失败且未恢复，需人工介入"
                        )
            except asyncio.CancelledError:
                logger.info("看门狗循环已停止")
                raise
            except Exception as e:
                # 看门狗自身异常不得导致循环终止
                logger.exception(f"看门狗检查发生未预期异常，将在下个周期继续: {e}")

    async def start(self, delayed_start: bool = False, delay_seconds: float = 5.0):
        self._process_start_time = time.monotonic()

        async def _delayed_startup():
            """启动触发任务，包裹 try/except 确保异常会将状态置为 FAILED。

            若不包裹，run_with_retry 抛出的未预期异常会让本协程静默死亡，
            而 _periodic_loop 会在初始轮询中无限等待 SUCCESS/FAILED 状态，导致
            定时器永远无法进入周期循环（静默挂起故障）。
            """
            try:
                await asyncio.sleep(delay_seconds)
                await self.run_with_retry(trigger="startup")
            except asyncio.CancelledError:
                logger.info("启动采集任务已取消")
                raise
            except Exception as e:
                logger.exception(f"启动采集任务发生未预期异常，已将状态置为失败: {e}")
                await self._update_status(
                    status=self.STATUS_FAILED,
                    step="启动失败",
                    message=f"启动采集未预期异常: {str(e)[:120]}",
                    finished_at=datetime.now().isoformat(),
                    error=str(e),
                )

        if delayed_start:
            self._startup_task = asyncio.create_task(_delayed_startup())
        else:
            async def _immediate_startup():
                try:
                    await self.run_with_retry(trigger="startup")
                except asyncio.CancelledError:
                    logger.info("启动采集任务已取消")
                    raise
                except Exception as e:
                    logger.exception(f"启动采集任务发生未预期异常，已将状态置为失败: {e}")
                    await self._update_status(
                        status=self.STATUS_FAILED,
                        step="启动失败",
                        message=f"启动采集未预期异常: {str(e)[:120]}",
                        finished_at=datetime.now().isoformat(),
                        error=str(e),
                    )
            self._startup_task = asyncio.create_task(_immediate_startup())

        self._periodic_task = asyncio.create_task(self._periodic_loop())
        self._watchdog_task = asyncio.create_task(self._watchdog_loop())

    async def close(self):
        if self._periodic_task and not self._periodic_task.done():
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                pass
        if self._watchdog_task and not self._watchdog_task.done():
            self._watchdog_task.cancel()
            try:
                await self._watchdog_task
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
