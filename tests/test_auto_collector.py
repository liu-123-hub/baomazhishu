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
    dashboard = make_valid_dashboard()
    dashboard["data_provenance"]["has_user_discussion"] = False
    return dashboard


def make_empty_dashboard() -> dict:
    return {
        "record_count": 0,
        "latest": {"date": "", "sectors": {}},
        "data_provenance": {"is_real_data": False, "has_user_discussion": False},
    }


class TestValidateDashboardForSync:

    def test_valid_dashboard_passes(self):
        dashboard = make_valid_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is True
        assert issues == []

    def test_empty_dashboard_rejected(self):
        dashboard = make_empty_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("sectors" in issue for issue in issues)

    def test_degraded_dashboard_rejected(self):
        dashboard = make_degraded_dashboard()
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("has_user_discussion" in issue or "降级" in issue for issue in issues)

    def test_non_dict_rejected(self):
        is_valid, issues = validate_dashboard_for_sync("not a dict")
        assert is_valid is False
        assert any("字典结构" in issue for issue in issues)

    def test_missing_top_level_fields_rejected(self):
        is_valid, issues = validate_dashboard_for_sync({"latest": {}})
        assert is_valid is False
        assert any("record_count" in issue for issue in issues)

    def test_all_sectors_zero_posts_rejected(self):
        dashboard = make_valid_dashboard()
        for s in dashboard["latest"]["sectors"].values():
            s["details"]["total_posts"] = 0
        is_valid, issues = validate_dashboard_for_sync(dashboard)
        assert is_valid is False
        assert any("完整性校验" in issue for issue in issues)


@pytest.fixture
def small_interval(monkeypatch):
    monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
    monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)
    return 0.3


def _make_recording_run_once(collector: AutoCollector, calls: List[dict],
                              fail_indices: set = None, exc: Exception = None):
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

    @pytest.mark.asyncio
    async def test_startup_triggers_first_update(self, small_interval, monkeypatch):
        collector = AutoCollector()
        calls: List[dict] = []
        monkeypatch.setattr(collector, "run_once", _make_recording_run_once(collector, calls))

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.15)

        startup_calls = [c for c in calls if c["trigger"] == "startup"]
        assert len(startup_calls) == 1, f"启动触发应执行 1 次，实际 {len(startup_calls)} 次: {calls}"

        await collector.close()


class TestPeriodicTriggerThreeCycles:

    @pytest.mark.asyncio
    async def test_three_periodic_cycles_with_timing(self, small_interval, monkeypatch):
        interval = small_interval
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

    @pytest.mark.asyncio
    async def test_timer_survives_exception_and_continues(self, small_interval, monkeypatch):
        interval = small_interval
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


class TestRunDeadline:

    @pytest.mark.asyncio
    async def test_deadline_timeout_recreates_executor_and_sets_failed(self, monkeypatch):
        collector = AutoCollector()
        old_executor = collector._executor

        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.2)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        def slow_pipeline():
            time.sleep(0.5)
            return {}
        monkeypatch.setattr(collector, "_run_pipeline_sync", slow_pipeline)

        async def mock_health_check():
            return {
                "details": [],
                "summary": {"reachable": 0, "total": 0, "unreachable": 0,
                            "skipped": 0, "all_unreachable": True},
            }
        import collectors.source_health_check as shc
        monkeypatch.setattr(shc, "run_health_check", mock_health_check)

        await collector.run_once(trigger="test")

        status = await collector.get_status()
        assert status["status"] == collector.STATUS_FAILED, (
            f"超时后状态应为 FAILED，实际: {status['status']}"
        )
        assert "采集超时" in status.get("error", ""), (
            f"错误信息应包含'采集超时'，实际: {status.get('error')}"
        )
        assert collector._executor is not old_executor, (
            "超时后执行器应被重建为新对象，避免卡死线程阻塞后续周期"
        )

        await asyncio.sleep(0.4)


class TestWatchdogMissedRun:

    @pytest.mark.asyncio
    async def test_watchdog_alerts_when_no_success_past_threshold(self, monkeypatch, caplog):
        collector = AutoCollector()

        monkeypatch.setattr(settings, "WATCHDOG_CHECK_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.1)
        monkeypatch.setattr(settings, "WATCHDOG_GRACE", 0.1)

        collector._process_start_time = time.monotonic() - 1.0

        caplog.set_level(logging.ERROR)

        watchdog_task = asyncio.create_task(collector._watchdog_loop())
        await asyncio.sleep(0.35)
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

        alert_messages = [r.message for r in caplog.records if "漏触发告警" in r.message]
        assert len(alert_messages) >= 1, (
            f"应记录至少 1 条漏触发告警，实际: {caplog.records}"
        )

    @pytest.mark.asyncio
    async def test_watchdog_no_alert_when_within_threshold(self, monkeypatch, caplog):
        collector = AutoCollector()

        monkeypatch.setattr(settings, "WATCHDOG_CHECK_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.1)
        monkeypatch.setattr(settings, "COLLECTOR_RUN_DEADLINE", 0.1)
        monkeypatch.setattr(settings, "WATCHDOG_GRACE", 0.1)

        collector._process_start_time = time.monotonic()

        caplog.set_level(logging.ERROR)

        watchdog_task = asyncio.create_task(collector._watchdog_loop())
        await asyncio.sleep(0.25)
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

        alert_messages = [r.message for r in caplog.records if "漏触发告警" in r.message]
        assert len(alert_messages) == 0, (
            f"uptime 未超过阈值时不应告警，实际记录: {alert_messages}"
        )


class TestStartupTaskExceptionHandling:

    @pytest.mark.asyncio
    async def test_startup_exception_sets_failed_status(self, monkeypatch):
        collector = AutoCollector()
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        async def failing_run_with_retry(trigger="scheduled"):
            raise RuntimeError("模拟启动采集未预期崩溃")
        monkeypatch.setattr(collector, "run_with_retry", failing_run_with_retry)

        await collector.start(delayed_start=False)

        await asyncio.sleep(0.2)

        status = await collector.get_status()
        assert status["status"] == collector.STATUS_FAILED, (
            f"启动异常后状态应为 FAILED，实际: {status['status']}"
        )
        assert status.get("step") == "启动失败", (
            f"step 应为'启动失败'，实际: {status.get('step')}"
        )
        assert "未预期异常" in status.get("message", ""), (
            f"message 应包含'未预期异常'，实际: {status.get('message')}"
        )

        await collector.close()

    @pytest.mark.asyncio
    async def test_periodic_loop_recovers_after_startup_exception(self, monkeypatch):
        collector = AutoCollector()
        monkeypatch.setattr(settings, "AUTO_COLLECT_INTERVAL", 0.3)
        monkeypatch.setattr(settings, "COLLECTOR_RETRY_TIMES", 0)

        call_count = {"n": 0}
        async def run_with_retry(trigger="scheduled"):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("模拟启动崩溃")
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

        await asyncio.sleep(0.2 + 2.2 + 0.4)

        await collector.close()

        assert call_count["n"] >= 2, (
            f"启动异常后 _periodic_loop 应恢复并触发后续周期，"
            f"实际 run_with_retry 调用 {call_count['n']} 次"
        )
