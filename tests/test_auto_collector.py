"""双触发机制数据自动更新功能的单元测试。"""
import asyncio
import logging
import os
import sys
import time
from datetime import datetime
from typing import List

import pytest

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from backend.app.auto_collector import AutoCollector
from backend.app.config import settings
from collectors.data_validation import validate_dashboard_for_sync


def make_valid_dashboard() -> dict:
    """构造一个能通过 validate_dashboard_for_sync 校验的合法 dashboard。"""
    return {
        "record_count": 1,
        "latest": {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "sectors": {
                "bank": {
                    "index": 55.0,
                    "interpretation": "中性偏多",
                    "details": {
                        "total_posts": 10,
                        "mom_buy_index": 30.0,
                        "mom_sell_index": 25.0,
                        "newbie_ratio": 20,
                    },
                },
                "securities": {
                    "index": 48.5,
                    "interpretation": "中性",
                    "details": {
                        "total_posts": 8,
                        "mom_buy_index": 20.0,
                        "mom_sell_index": 28.0,
                        "newbie_ratio": 15,
                    },
                },
            },
        },
        "data_provenance": {
            "is_real_data": True,
            "has_user_discussion": True,
            "fingerprints": [],
        },
        "data_sources": {},
    }


def make_degraded_dashboard() -> dict:
    """构造一个降级 dashboard（无用户讨论数据），应被校验门拒绝。"""
    dashboard = make_valid_dashboard()
    dashboard["data_provenance"]["has_user_discussion"] = False
    return dashboard


def make_empty_dashboard() -> dict:
    """构造一个空 dashboard（无板块数据），应被校验门拒绝。"""
    return {
        "record_count": 0,
        "latest": {"date": "", "sectors": {}},
        "data_provenance": {"is_real_data": False, "has_user_discussion": False},
    }


class TestValidateDashboardForSync:
    """validate_dashboard_for_sync校验逻辑测试。"""

    def test_valid_dashboard_passes(self):
        """合法 dashboard（有板块、有帖子、有用户讨论）应通过校验。"""
        dashboard = make_valid_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is True
        assert issues == []

    def test_empty_dashboard_rejected(self):
        """空 dashboard（无板块数据）应被拒绝。"""
        dashboard = make_empty_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("sectors" in issue for issue in issues)

    def test_degraded_dashboard_rejected(self):
        """降级dashboard（无用户讨论）应被拒绝。"""
        dashboard = make_degraded_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("has_user_discussion" in issue or "降级" in issue for issue in issues)

    def test_non_dict_rejected(self):
        """非字典结构应被立即拒绝。"""
        is_valid, issues = validate_dashboard_for_sync("not a dict")
        assert is_valid is False
        assert any("字典结构" in issue for issue in issues)

    def test_missing_top_level_fields_rejected(self):
        """缺少顶层字段应被拒绝。"""
        is_valid, issues = validate_dashboard_for_sync({"latest": {}})
        assert is_valid is False
        assert any("record_count" in issue for issue in issues)

    def test_all_sectors_zero_posts_rejected(self):
        """所有板块 total_posts=0 应被拒绝。"""
        dashboard = make_valid_dashboard()
        for s in dashboard["latest"]["sectors"].values():
            s["details"]["total_posts"] = 0
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("完整性校验" in issue for issue in issues)


@pytest.fixture
def small_interval(monkeypatch):
    """缩小定时采集间隔和重试次数，加速测试。"""
    monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
    monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)
    return 0.3


def _make_recording_run_once(collector: AutoCollector, calls: List[dict],
                              fail_indices: set = None, exc: Exception = None):
    """生成记录调用并可控失败的run_once替身。"""
    fail_indices = fail_indices or set()

    async def mock_run_once(trigger: str = "scheduled"):
        call_index = len(calls) + 1
        calls.append({
            "trigger": trigger,
            "timestamp": time.monotonic(),
            "index": call_index,
        })
        if call_index in fail_indices:
            raise exc or RuntimeError(f"模拟第 {call_index} 次采集网络异常")
        await collector._update_status(
            status=collector.STATUS_SUCCESS,
            progress=100,
            step="完成",
            message="模拟采集成功",
            finished_at=datetime.now().isoformat(),
        )

    return mock_run_once


class TestStartupTrigger:
    """程序启动触发首次数据更新测试。"""

    @pytest.mark.asyncio
    async def test_startup_triggers_first_update(self, small_interval, monkeypatch):
        """启动后应立即触发一次 trigger='startup' 的数据更新。"""
        collector = AutoCollector()
        calls: List[dict] = []
        monkeypatch.setattr(collector, "run_once", _make_recording_run_once(collector, calls))

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.15)

        startup_calls = [c for c in calls if c["trigger"] == "startup"]
        assert len(startup_calls) == 1, f"启动触发应执行 1 次，实际 {len(startup_calls)} 次: {calls}"

        await collector.close()


class TestPeriodicTriggerThreeCycles:
    """连续3个定时周期触发时间测试。"""

    @pytest.mark.asyncio
    async def test_three_periodic_cycles_with_timing(self, small_interval, monkeypatch):
        """验证连续 3 个定时周期的触发间隔符合配置的时间要求。"""
        interval = small_interval  # 0.3 秒
        collector = AutoCollector()
        calls: List[dict] = []
        monkeypatch.setattr(collector, "run_once", _make_recording_run_once(collector, calls))

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.15 + interval * 3 + 0.3)

        await collector.close()

        scheduled_calls = [c for c in calls if c["trigger"] == "scheduled"]
        assert len(scheduled_calls) >= 3, (
            f"定时触发应至少 3 次，实际 {len(scheduled_calls)} 次: {calls}"
        )

        tolerances = 0.15
        for i in range(1, min(len(scheduled_calls), 3)):
            gap = scheduled_calls[i]["timestamp"] - scheduled_calls[i - 1]["timestamp"]
            assert abs(gap - interval) <= tolerances, (
                f"第 {i} 个定时周期与上一个的间隔 {gap:.3f}s "
                f"偏离配置值 {interval}s 超过容差 {tolerances}s"
            )

        startup_calls = [c for c in calls if c["trigger"] == "startup"]
        assert len(startup_calls) == 1
        gap_startup_to_first_scheduled = scheduled_calls[0]["timestamp"] - startup_calls[0]["timestamp"]
        assert gap_startup_to_first_scheduled >= interval - tolerances, (
            f"启动触发到首次定时触发的间隔 {gap_startup_to_first_scheduled:.3f}s "
            f"应不小于约 1 个周期 {interval}s"
        )


class TestPeriodicTimerStabilityOnException:
    """异常场景下定时器稳定性测试。"""

    @pytest.mark.asyncio
    async def test_timer_survives_exception_and_continues(self, small_interval, monkeypatch):
        """定时器在某次更新异常后不应终止，下一个周期仍能正常触发。"""
        interval = small_interval  # 0.3 秒
        collector = AutoCollector()
        calls: List[dict] = []

        monkeypatch.setattr(
            collector, "run_once",
            _make_recording_run_once(collector, calls, fail_indices={2},
                                     exc=RuntimeError("模拟网络异常/请求超时"))
        )

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.15 + interval * 3 + 0.3)

        await collector.close()

        assert len(calls) >= 4, (
            f"异常后定时器应继续运行，总调用应 >= 4 次，实际 {len(calls)} 次: {calls}"
        )

        assert calls[1]["index"] == 2, f"第 2 次调用应为异常点，实际 index={calls[1]['index']}"

        scheduled_after_failure = [
            c for c in calls[2:] if c["trigger"] == "scheduled"
        ]
        assert len(scheduled_after_failure) >= 2, (
            f"异常后应至少有 2 次定时触发，实际 {len(scheduled_after_failure)} 次: {calls}"
        )

    @pytest.mark.asyncio
    async def test_timer_survives_consecutive_exceptions(self, small_interval, monkeypatch):
        """连续多次异常后定时器仍不应终止。"""
        interval = small_interval
        collector = AutoCollector()
        calls: List[dict] = []

        monkeypatch.setattr(
            collector, "run_once",
            _make_recording_run_once(collector, calls, fail_indices={2, 3, 4},
                                     exc=ConnectionError("模拟请求超时"))
        )

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.15 + interval * 4 + 0.3)

        await collector.close()

        assert len(calls) >= 5, (
            f"连续异常后定时器应继续运行，总调用应 >= 5 次，实际 {len(calls)} 次: {calls}"
        )

        assert calls[4]["index"] == 5


# ============================================================
# 场景 4：单次采集运行超时（deadline）机制
# ============================================================

class TestRunDeadline:
    """验证 run_in_executor 的 deadline 超时保护：卡死的采集应被放弃，执行器重建。"""

    @pytest.mark.asyncio
    async def test_deadline_timeout_recreates_executor_and_sets_failed(self, monkeypatch):
        """采集超过 COLLECTOR_RUN_DEADLINE 应被放弃，执行器被重建，状态置为 FAILED。"""
        collector = AutoCollector()
        old_executor = collector._executor

        # 设置极短的 deadline（0.2s）和不重试
        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.2)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        # _run_pipeline_sync 模拟卡死（sleep 时间 > deadline）
        def slow_pipeline():
            time.sleep(0.5)
            return {}
        monkeypatch.setattr(collector, "_run_pipeline_sync", slow_pipeline)

        # 预检设为即时返回，避免真实网络调用拖慢测试
        async def mock_health_check():
            return {
                "details": [],
                "summary": {"reachable": 0, "total": 0, "unreachable": 0,
                            "skipped": 0, "all_unreachable": True},
            }
        import collectors.source_health_check as shc
        monkeypatch.setattr(shc, "run_health_check", mock_health_check)

        # 直接调用 run_once 隔离测试 deadline（run_once 内部捕获异常并置 FAILED，不向上抛出）
        await collector.run_once(trigger="test")

        status = await collector.get_status()
        assert status["status"] == collector.STATUS_FAILED, (
            f"超时后状态应为 FAILED，实际: {status['status']}"
        )
        assert "采集超时" in status.get("error", ""), (
            f"错误信息应包含'采集超时'，实际: {status.get('error')}"
        )
        # 关键断言：执行器已被重建（新对象），确保下一周期不会被卡死线程阻塞
        assert collector._executor is not old_executor, (
            "超时后执行器应被重建为新对象，避免卡死线程阻塞后续周期"
        )

        # 等待孤儿线程结束，避免 pytest 退出时被非守护线程挂起
        await asyncio.sleep(0.4)


# ============================================================
# 场景 5：看门狗漏触发检测
# ============================================================

class TestWatchdogMissedRun:
    """验证看门狗在长期无成功运行时发出 ERROR 告警（"a job that never fires emits no error"）。"""

    @pytest.mark.asyncio
    async def test_watchdog_alerts_when_no_success_past_threshold(self, monkeypatch, caplog):
        """自启动以来从未成功且 uptime 超过阈值时，看门狗应记录漏触发告警。"""
        collector = AutoCollector()

        # 设置极小的阈值：missed_threshold = 0.1+0.1+0.1 = 0.3s
        monkeypatch.setattr(settings, "WATCHDOG_CHECK_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.1)
        monkeypatch.setattr(settings, "WATCHDOG_GRACE", 0.1)

        # 进程启动时刻设为 1 秒前（uptime=1s > missed_threshold=0.3s）
        collector._process_start_time = time.monotonic() - 1.0
        # last_success_at 保持 None（从未成功过）

        caplog.set_level(logging.ERROR)

        watchdog_task = asyncio.create_task(collector._watchdog_loop())
        # 等待看门狗完成至少一次检查（首次 sleep 0.1s + 检查逻辑）
        await asyncio.sleep(0.35)
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

        # 验证漏触发告警已记录
        alert_messages = [r.message for r in caplog.records if "漏触发告警" in r.message]
        assert len(alert_messages) >= 1, (
            f"应记录至少 1 条漏触发告警，实际: {caplog.records}"
        )

    @pytest.mark.asyncio
    async def test_watchdog_no_alert_when_within_threshold(self, monkeypatch, caplog):
        """uptime 未超过阈值时，看门狗不应发出漏触发告警（避免误报）。"""
        collector = AutoCollector()

        monkeypatch.setattr(settings, "WATCHDOG_CHECK_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.1)
        monkeypatch.setattr(settings, "WATCHDOG_GRACE", 0.1)
        # missed_threshold = 0.3s

        # 进程刚启动（uptime ≈ 0s < 0.3s），不应告警
        collector._process_start_time = time.monotonic()

        caplog.set_level(logging.ERROR)

        watchdog_task = asyncio.create_task(collector._watchdog_loop())
        await asyncio.sleep(0.25)  # 看门狗检查一次，但 uptime 仍 < 阈值
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

        alert_messages = [r.message for r in caplog.records if "漏触发告警" in r.message]
        assert len(alert_messages) == 0, (
            f"uptime 未超过阈值时不应告警，实际记录: {alert_messages}"
        )


# ============================================================
# 场景 6：启动采集任务未预期异常的处理
# ============================================================

class TestStartupTaskExceptionHandling:
    """验证 run_with_retry 抛出未预期异常时，启动包装器将状态置为 FAILED。

    关键修复点：若不包裹，_periodic_loop 会在初始轮询中无限等待
    SUCCESS/FAILED 状态，导致定时器永远无法进入周期循环（静默挂起故障）。
    """

    @pytest.mark.asyncio
    async def test_startup_exception_sets_failed_status(self, monkeypatch):
        """启动任务未预期异常后，状态应被显式置为 FAILED。"""
        collector = AutoCollector()
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        # run_with_retry 抛出未预期异常（模拟 run_once 之外的未预期崩溃）
        async def failing_run_with_retry(trigger="scheduled"):
            raise RuntimeError("模拟启动采集未预期崩溃")
        monkeypatch.setattr(collector, "run_with_retry", failing_run_with_retry)

        await collector.start(delayed_start=False)

        # 等待启动任务执行（_immediate_startup 立即调用 run_with_retry）
        await asyncio.sleep(0.2)

        status = await collector.get_status()
        # 关键断言：状态应为 FAILED（而非 IDLE/RUNNING），否则 _periodic_loop 会无限等待
        assert status["status"] == collector.STATUS_FAILED, (
            f"启动异常后状态应为 FAILED，实际: {status['status']}"
        )
        # step 字段标识启动失败路径，message 字段包含未预期异常描述
        assert status.get("step") == "启动失败", (
            f"step 应为'启动失败'，实际: {status.get('step')}"
        )
        assert "未预期异常" in status.get("message", ""), (
            f"message 应包含'未预期异常'，实际: {status.get('message')}"
        )

        await collector.close()

    @pytest.mark.asyncio
    async def test_periodic_loop_recovers_after_startup_exception(self, monkeypatch):
        """启动异常置 FAILED 后，_periodic_loop 应能退出初始等待并进入周期循环。"""
        collector = AutoCollector()
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        # 首次 run_with_retry（startup）抛异常，后续 run_with_retry（scheduled）正常
        call_count = {"n": 0}
        async def run_with_retry(trigger="scheduled"):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("模拟启动崩溃")
            # 后续 scheduled 调用走正常路径：调用 run_once（mock 为成功）
            await collector.run_once(trigger=trigger)

        async def mock_run_once(trigger="scheduled"):
            await collector._update_status(
                status=collector.STATUS_SUCCESS,
                progress=100,
                step="完成",
                message="模拟成功",
                finished_at=datetime.now().isoformat(),
            )
        monkeypatch.setattr(collector, "run_with_retry", run_with_retry)
        monkeypatch.setattr(collector, "run_once", mock_run_once)

        await collector.start(delayed_start=False)

        # 等待：启动异常(0.2s) + _periodic_loop 轮询发现 FAILED(最多2s) + 首个周期(0.3s)
        # 为加速，将轮询等待也缩短：直接等待足够时间
        await asyncio.sleep(0.2 + 2.2 + 0.4)

        await collector.close()

        # 验证：startup 调用了 1 次，且后续有 scheduled 调用（说明 _periodic_loop 恢复了）
        assert call_count["n"] >= 2, (
            f"启动异常后 _periodic_loop 应恢复并触发后续周期，"
            f"实际 run_with_retry 调用 {call_count['n']} 次"
        )
