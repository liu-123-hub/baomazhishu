"""核心 Logger 模块测试"""

import json
import os
import sys
import time
import threading

import pytest

import mini_logger
from mini_logger import (
    init,
    get_logger,
    debug,
    info,
    warn,
    error,
    fatal,
    set_level,
    bind_context,
    clear_context,
    shutdown,
    catch_exception,
)
from mini_logger.config import LogLevel, LogConfig
from mini_logger.core import Logger


@pytest.fixture(autouse=True)
def reset_logger():
    """每个用例前后重置全局 Logger。"""
    clear_context()
    shutdown()
    yield
    shutdown()
    clear_context()


def _wait_flush(timeout: float = 1.0):
    """等待后台线程 flush（轮询队列空 + flush 文件）。"""
    logger = get_logger()
    deadline = time.time() + timeout
    while time.time() < deadline:
        if logger._queue.qsize() == 0:
            break
        time.sleep(0.005)
    # 主动 flush
    for h in logger.handlers:
        h.flush()


class TestInit:
    def test_init_returns_logger(self, tmp_path):
        lg = init(service="t", log_dir=str(tmp_path), file=True)
        assert isinstance(lg, Logger)

    def test_init_replaces_previous(self, tmp_path):
        lg1 = init(service="t1", log_dir=str(tmp_path), file=True)
        lg2 = init(service="t2", log_dir=str(tmp_path), file=True)
        assert lg1 is not lg2
        assert get_logger().config.service == "t2"

    def test_init_with_str_level(self, tmp_path):
        init(service="t", level="DEBUG", log_dir=str(tmp_path))
        assert get_logger().level == LogLevel.DEBUG


class TestModuleLevelAPI:
    def test_info_logs_to_file(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        info("hello world")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        assert files
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            content = f.read()
        rec = json.loads(content.splitlines()[0])
        assert rec["msg"] == "hello world"
        assert rec["level"] == "INFO"
        assert rec["service"] == "t"
        assert "trace_id" in rec

    def test_all_five_levels(self, tmp_path):
        init(service="t", level="DEBUG", console=False, file=True, log_dir=str(tmp_path))
        debug("d"); info("i"); warn("w")
        error("e"); fatal("f")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        levels = [r["level"] for r in lines]
        for lvl in ("DEBUG", "INFO", "WARN", "ERROR", "FATAL"):
            assert lvl in levels

    def test_level_filtering(self, tmp_path):
        init(service="t", level="WARN", console=False, file=True, log_dir=str(tmp_path))
        debug("d"); info("i"); warn("w")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        levels = [r["level"] for r in lines]
        assert "DEBUG" not in levels
        assert "INFO" not in levels
        assert "WARN" in levels

    def test_extra_fields(self, tmp_path):
        init(service="t", level="DEBUG", console=False, file=True, log_dir=str(tmp_path))
        info("msg", user_id="u1", action="login", count=42)
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["extra"]["action"] == "login"
        assert rec["extra"]["count"] == 42


class TestContextInjection:
    def test_trace_id_from_context(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        bind_context(trace_id="trace-abc-123", user_id="user-x", client_ip="1.2.3.4")
        info("ctx test")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["trace_id"] == "trace-abc-123"
        assert rec["user_id"] == "user-x"
        assert rec["client_ip"] == "1.2.3.4"

    def test_auto_trace_id_when_unbound(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        info("no ctx")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["trace_id"] and len(rec["trace_id"]) == 32


class TestLocationCapture:
    def test_module_func_line_captured(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), include_location=True)
        info("loc")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["module"]
        assert rec["func"]
        assert rec["line"] > 0
        assert rec["module"] == __name__

    def test_location_disabled(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), include_location=False)
        info("loc")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert "module" not in rec
        assert "func" not in rec


class TestExceptionCapture:
    def test_error_with_exc(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        try:
            raise ValueError("bad value")
        except ValueError as e:
            error("err", exc=e)
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["err_type"] == "ValueError"
        assert "bad value" in rec["err_stack"]
        assert "Traceback" in rec["err_stack"]

    def test_exception_method_auto_captures(self, tmp_path):
        from mini_logger.core import Logger
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            get_logger().exception("auto captured")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["err_type"] == "RuntimeError"
        assert "boom" in rec["err_stack"]

    def test_catch_exception_decorator_reraise(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")

        @catch_exception("decorator err", reraise=True)
        def boom():
            raise ValueError("decorated")

        with pytest.raises(ValueError):
            boom()
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["msg"] == "decorator err"
        assert rec["err_type"] == "ValueError"

    def test_catch_exception_decorator_swallow(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")

        @catch_exception("swallow", reraise=False)
        def boom():
            raise ValueError("decorated")

        result = boom()  # 不应抛
        assert result is None
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["msg"] == "swallow"


class TestDynamicLevel:
    def test_set_level_int(self, tmp_path):
        init(service="t", level="INFO", console=False, file=True, log_dir=str(tmp_path))
        set_level(LogLevel.DEBUG)
        assert get_logger().level == LogLevel.DEBUG
        debug("now visible")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert any(r["level"] == "DEBUG" for r in lines)

    def test_set_level_str(self, tmp_path):
        init(service="t", level="DEBUG", console=False, file=True, log_dir=str(tmp_path))
        set_level("WARN")
        assert get_logger().level == LogLevel.WARN


class TestSensitiveRedaction:
    def test_idcard_in_msg_redacted(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        info("user id=110101199003078888 ok")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert "110101199003078888" not in rec["msg"]

    def test_phone_in_extra_redacted(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        info("call", phone="13812345678")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert "13812345678" not in rec["extra"]["phone"]

    def test_password_field_redacted(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        info("login", password="s3cret", username="bob")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert rec["extra"]["password"] == "***"
        assert rec["extra"]["username"] == "bob"

    def test_redact_disabled(self, tmp_path):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            redact_enabled=False,
        )
        info("phone=13812345678")
        _wait_flush()
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            rec = json.loads(f.read().splitlines()[0])
        assert "13812345678" in rec["msg"]


class TestBackpressure:
    def test_debug_dropped_when_water_high(self, tmp_path):
        # 极小队列 + 极低水位阈值，触发 DEBUG 丢弃
        init(
            service="t",
            level="DEBUG",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            queue_maxsize=4,
            backpressure_warn=0.25,
            backpressure_drop=0.95,
            drop_policy="oldest",
            flush_interval=0.5,  # 不让后台消费太快
        )
        # 灌入大量 INFO 占满队列
        for i in range(20):
            info(f"info-{i}")
        # DEBUG 此时应被丢弃
        debug("should-drop")
        _wait_flush(timeout=2.0)
        # shutdown 触发 drain
        shutdown(timeout=2.0)
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            content = f.read()
        assert "should-drop" not in content

    def test_oldest_dropped_when_full(self, tmp_path):
        init(
            service="t",
            level="INFO",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            queue_maxsize=2,
            drop_policy="oldest",
            flush_interval=0.5,
        )
        for i in range(20):
            info(f"msg-{i}")
        shutdown(timeout=2.0)
        # 队列被反复 pop 最旧后塞新，最终应有部分消息落盘
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            content = f.read()
        assert "msg-" in content


class TestShutdown:
    def test_shutdown_drains_queue(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), flush_interval=0.5)
        for i in range(10):
            info(f"msg-{i}")
        shutdown(timeout=2.0)
        files = os.listdir(str(tmp_path))
        with open(os.path.join(str(tmp_path), files[0]), encoding="utf-8") as f:
            content = f.read()
        # 至少部分 msg 应被 drain 出来
        assert "msg-" in content

    def test_shutdown_idempotent(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        shutdown()
        shutdown()  # 不应抛异常

    def test_get_logger_lazy_init(self):
        shutdown()
        lg = get_logger()
        assert isinstance(lg, Logger)
        # 默认 service
        assert lg.config.service == "default-service"


class TestExcepthook:
    def test_excepthook_installed(self, tmp_path):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            catch_unhandled=True,
            level="DEBUG",
        )
        assert sys.excepthook is not sys.__excepthook__

    def test_excepthook_disabled(self, tmp_path):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            catch_unhandled=False,
        )
        assert sys.excepthook is sys.__excepthook__
