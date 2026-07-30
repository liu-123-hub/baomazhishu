"""端到端集成测试：模拟真实业务场景接入"""

import json
import os
import time

import pytest

import mini_logger
from mini_logger import init, info, error, bind_context, clear_context, shutdown, get_logger


@pytest.fixture(autouse=True)
def reset_logger():
    clear_context()
    shutdown()
    yield
    shutdown()
    clear_context()


def _wait_flush(timeout: float = 1.0):
    logger = get_logger()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if logger._queue.qsize() == 0:
            break
        time.sleep(0.005)
    for h in logger.handlers:
        h.flush()


def _read_records(log_dir):
    """读取目录下所有日志文件的记录列表。"""
    records = []
    for f in sorted(os.listdir(log_dir)):
        if not f.endswith(".log"):
            continue
        with open(os.path.join(log_dir, f), encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


class TestScenarioFastAPILike:
    """模拟 FastAPI 中间件接入：每个请求注入 trace_id，业务日志自动携带。"""

    def test_request_trace_propagation(self, tmp_path):
        init(
            service="api-server",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
        )
        # 模拟 2 个请求
        for rid in ("req-001", "req-002"):
            token = bind_context(
                trace_id=rid,
                request_id=rid,
                user_id=f"user-{rid}",
                client_ip=f"10.0.0.{rid[-1]}",
            )
            try:
                info("request start", path="/api/data")
                info("processing")
                if rid == "req-002":
                    try:
                        raise RuntimeError("db timeout")
                    except RuntimeError as e:
                        error("processing failed", exc=e)
                info("request end")
            finally:
                token.reset()
                clear_context()

        _wait_flush()
        records = _read_records(str(tmp_path))

        r1 = [r for r in records if r["trace_id"] == "req-001"]
        r2 = [r for r in records if r["trace_id"] == "req-002"]
        assert len(r1) == 3  # 3 条 INFO
        assert len(r2) == 4  # 3 INFO + 1 ERROR
        # 找到 ERROR 记录验证异常类型
        err_record = [r for r in r2 if r["level"] == "ERROR"][0]
        assert err_record["err_type"] == "RuntimeError"
        assert r2[0]["client_ip"] == "10.0.0.2"

    def test_parallel_requests_isolated(self, tmp_path):
        """并发请求 trace_id 互不污染。"""
        import threading

        init(
            service="api-server",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
        )

        def fake_request(rid):
            token = bind_context(trace_id=rid)
            try:
                info("start", rid=rid)
                time.sleep(0.02)
                info("end", rid=rid)
            finally:
                token.reset()
                clear_context()

        threads = [threading.Thread(target=fake_request, args=(f"tid-{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        _wait_flush(timeout=2.0)
        records = _read_records(str(tmp_path))
        # 每个线程 2 条日志，且 trace_id 匹配
        for i in range(5):
            tid = f"tid-{i}"
            tid_records = [r for r in records if r["trace_id"] == tid]
            assert len(tid_records) == 2
            assert tid_records[0]["extra"]["rid"] == tid


class TestScenarioCollector:
    """模拟数据采集器场景：长任务、批量采集、异常容错。"""

    def test_collector_progress_logging(self, tmp_path):
        init(
            service="collector",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
        )
        bind_context(trace_id="collect-20260731")

        try:
            info("collector start", source="guba", batch_size=100)
            for i in range(5):
                info("batch done", batch=i, count=20)
            info("collector done", total=100)
        finally:
            clear_context()

        _wait_flush()
        records = _read_records(str(tmp_path))
        # 7 条记录：1 start + 5 batch + 1 done
        assert len(records) == 7
        assert records[0]["extra"]["source"] == "guba"
        assert records[-1]["extra"]["total"] == 100
        # 所有记录同 trace_id
        assert all(r["trace_id"] == "collect-20260731" for r in records)

    def test_collector_partial_failure(self, tmp_path):
        init(
            service="collector",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
        )
        bind_context(trace_id="partial-fail")

        try:
            sources = ["guba", "xueqiu", "xhs"]
            for s in sources:
                try:
                    if s == "xhs":
                        raise ConnectionError(f"{s} unreachable")
                    info(f"{s} ok", source=s)
                except ConnectionError as e:
                    error(f"{s} failed", exc=e, source=s)
        finally:
            clear_context()

        _wait_flush()
        records = _read_records(str(tmp_path))
        # guba ok / xueqiu ok / xhs error
        assert len(records) == 3
        err_record = [r for r in records if r["level"] == "ERROR"][0]
        assert err_record["err_type"] == "ConnectionError"
        assert err_record["extra"]["source"] == "xhs"


class TestScenarioStandaloneScript:
    """模拟独立脚本场景：1 行 init、无需复杂配置。"""

    def test_minimal_init(self, tmp_path):
        # 最简调用：1 行 init
        init(service="my-script", console=False, file=True, log_dir=str(tmp_path))
        info("script started")
        info("doing work")
        info("script done")
        shutdown()

        records = _read_records(str(tmp_path))
        assert len(records) == 3
        assert records[0]["msg"] == "script started"
        assert records[0]["service"] == "my-script"

    def test_auto_trace_id_for_standalone(self, tmp_path):
        init(service="my-script", console=False, file=True, log_dir=str(tmp_path))
        info("auto tid")
        shutdown()
        records = _read_records(str(tmp_path))
        assert len(records[0]["trace_id"]) == 32


class TestJsonFormat:
    def test_log_record_is_valid_json(self, tmp_path):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
        )
        info("test json", key="value", num=42, flag=True)
        _wait_flush()
        records = _read_records(str(tmp_path))
        rec = records[0]
        assert rec["msg"] == "test json"
        assert rec["extra"]["key"] == "value"
        assert rec["extra"]["num"] == 42
        assert rec["extra"]["flag"] is True

    def test_log_record_has_all_required_fields(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        info("required fields")
        _wait_flush()
        records = _read_records(str(tmp_path))
        rec = records[0]
        # 必填字段
        for f in ("ts", "level", "service", "trace_id", "msg"):
            assert f in rec, f"missing required field: {f}"
        # ts 含 +08:00 时区
        assert "+08:00" in rec["ts"]


class TestMessageTruncation:
    def test_long_message_truncated(self, tmp_path):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            max_msg_bytes=200,
            level="INFO",
        )
        long_msg = "x" * 1000
        info(long_msg)
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            content = f.read()
        assert "<truncated>" in content
        # 实际落盘字节远小于 1000+元数据
        assert len(content) < 1000
