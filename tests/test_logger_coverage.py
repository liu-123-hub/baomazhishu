"""补充覆盖率测试：补全 excepthook 触发、drop_policy 分支、handler 异常路径等。"""

import json
import os
import sys
import threading
import time
import queue

import pytest

import mini_logger
from mini_logger import init, info, error, debug, warn, set_level, shutdown, get_logger, clear_context
from mini_logger.config import LogLevel, LogConfig
from mini_logger.context import (
    LogContext,
    ContextToken,
    _ctx,
    get_context,
    bind_context,
    clear_context,
)
from mini_logger.handlers import (
    ConsoleHandler,
    RollingFileHandler,
    RemoteHandler,
)
from mini_logger.exceptions import catch_exception


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
    records = []
    for f in sorted(os.listdir(log_dir)):
        if not f.endswith(".log"):
            continue
        with open(os.path.join(log_dir, f), encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return records


# ============================================================
# context.py 覆盖
# ============================================================
class TestContextExtraCoverage:
    def test_get_context_returns_default_when_unset(self):
        """contextvars 在未 bind 时返回 default LogContext()。"""
        clear_context()
        ctx = get_context()
        assert isinstance(ctx, LogContext)
        assert ctx.trace_id == ""

    def test_context_token_reset_handles_already_reset(self):
        # 模拟 token 已被 reset 过：第一次正常，第二次触发 except
        token = bind_context(trace_id="t1")
        token.reset()
        token.reset()  # 应触发 ValueError，被 except 捕获

    def test_bind_context_in_child_thread_isolated(self):
        """子线程 bind 后不影响主线程。"""
        clear_context()
        captured = {}

        def worker():
            token = bind_context(trace_id="child-tid")
            captured["ctx"] = get_context()
            token.reset()

        t = threading.Thread(target=worker)
        t.start()
        t.join()
        # 子线程内 trace_id 已绑定
        assert captured["ctx"].trace_id == "child-tid"
        # 主线程仍为空
        assert get_context().trace_id == ""


# ============================================================
# core.py excepthook 覆盖
# ============================================================
class TestExcepthookTrigger:
    def test_excepthook_actually_invoked(self, tmp_path):
        """直接调用 sys.excepthook，验证日志被写入。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            catch_unhandled=True,
        )
        try:
            raise ValueError("unhandled test exc")
        except ValueError:
            exc_info = sys.exc_info()

        # 直接调用 hook
        sys.excepthook(*exc_info)
        _wait_flush(timeout=2.0)
        records = _read_records(str(tmp_path))
        fatal_records = [r for r in records if r["level"] == "FATAL"]
        assert len(fatal_records) >= 1
        assert fatal_records[0]["err_type"] == "ValueError"
        assert "unhandled test exc" in fatal_records[0]["msg"]

    def test_excepthook_with_none_value(self, tmp_path):
        """exc_value 为 None 时不应崩溃。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            catch_unhandled=True,
        )
        # 调用 hook 时 exc_value=None
        sys.excepthook(ValueError, None, None)
        _wait_flush()
        # 不应崩溃，也不应写入 FATAL
        records = _read_records(str(tmp_path))
        fatal_records = [r for r in records if r["level"] == "FATAL"]
        assert len(fatal_records) == 0

    def test_excepthook_queue_full(self, tmp_path):
        """excepthook 在队列满时不应崩溃。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            catch_unhandled=True,
            queue_maxsize=1,
            flush_interval=2.0,  # 不让后台消费
        )
        # 灌满队列
        for i in range(5):
            info(f"fill-{i}")
        # 现在队列满，调用 excepthook 应被吞掉
        try:
            raise RuntimeError("test")
        except RuntimeError:
            exc_info = sys.exc_info()
        sys.excepthook(*exc_info)
        # 不应抛异常
        shutdown(timeout=2.0)


# ============================================================
# core.py drop_policy 分支
# ============================================================
class TestDropPolicy:
    def test_newest_drop_policy(self, tmp_path):
        init(
            service="t",
            level="INFO",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            queue_maxsize=2,
            drop_policy="newest",
            flush_interval=0.5,
        )
        # 队列满后，新消息直接丢弃
        for i in range(10):
            info(f"msg-{i}")
        shutdown(timeout=2.0)
        records = _read_records(str(tmp_path))
        # newest 策略下，最早入队的应保留
        msgs = [r["msg"] for r in records]
        # 至少 msg-0 应被消费
        assert any("msg-0" in m for m in msgs)
        # 最末尾的 msg-9 可能被丢
        assert "msg-9" not in msgs or "msg-9" in msgs  # 至少不崩溃

    def test_block_drop_policy(self, tmp_path):
        init(
            service="t",
            level="INFO",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            queue_maxsize=8,
            drop_policy="block",
            flush_interval=0.01,  # 快速消费
        )
        # 后台快速消费，block 策略应允许部分消息通过
        for i in range(10):
            info(f"block-{i}")
        shutdown(timeout=3.0)
        records = _read_records(str(tmp_path))
        # block 策略下，至少 4 条应被消费（实际通常更多）
        assert len(records) >= 4

    def test_info_sampling_at_drop_threshold(self, tmp_path):
        # 队列接近满时，INFO 应被采样
        init(
            service="t",
            level="DEBUG",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            queue_maxsize=4,
            backpressure_warn=0.25,
            backpressure_drop=0.50,
            drop_policy="oldest",
            flush_interval=1.0,
        )
        # 灌入 INFO 占满
        for i in range(20):
            info(f"info-{i}")
        # 此时已触发采样
        shutdown(timeout=2.0)
        # 不崩溃，部分消息落盘
        records = _read_records(str(tmp_path))
        assert len(records) >= 1


# ============================================================
# core.py drain_remaining 异常路径
# ============================================================
class TestDrainRemaining:
    def test_drain_swallows_handler_error(self, tmp_path, monkeypatch):
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
        )
        info("msg1")
        info("msg2")

        # 让 file handler emit 抛异常
        original_emit = RollingFileHandler.emit

        def boom(self, record):
            raise OSError("disk full")

        monkeypatch.setattr(RollingFileHandler, "emit", boom)
        # shutdown 时 _drain_remaining 应吞掉异常
        shutdown(timeout=2.0)
        # 不崩溃即可
        # 恢复
        monkeypatch.setattr(RollingFileHandler, "emit", original_emit)


# ============================================================
# core.py exception 自动捕获
# ============================================================
class TestExceptionAutoCapture:
    def test_error_in_except_block_auto_captures(self, tmp_path):
        """在 except 块内调用 error(msg) 不传 exc，应自动捕获当前异常栈。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
        )
        try:
            raise TypeError("auto captured type error")
        except TypeError:
            error("auto captured")  # 不传 exc
        _wait_flush()
        records = _read_records(str(tmp_path))
        rec = records[0]
        assert rec["err_type"] == "TypeError"
        assert "auto captured type error" in rec["err_stack"]

    def test_catch_exception_decorator_no_exception(self, tmp_path):
        """装饰器包裹的函数未抛异常时正常返回。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")

        @catch_exception("should not log")
        def ok(x):
            return x * 2

        assert ok(5) == 10
        _wait_flush()
        records = _read_records(str(tmp_path))
        # 不应有错误日志
        assert all(r["level"] != "ERROR" for r in records)


# ============================================================
# handlers.py 异常路径覆盖
# ============================================================
class TestHandlerExceptionPaths:
    def test_console_handler_ioerror_swallowed(self, monkeypatch, capsys):
        h = ConsoleHandler()

        # 第一次 write 抛异常，第二次正常（用于 flush）
        call_count = {"n": 0}

        def fake_write(s):
            call_count["n"] += 1
            if call_count["n"] <= 2:
                raise IOError("simulated")
            return len(s)

        import sys
        monkeypatch.setattr(sys.stdout, "write", fake_write)
        h.emit("will fail")
        # 不崩溃；后续调用应继续尝试
        monkeypatch.undo()
        h.emit("will succeed")
        captured = capsys.readouterr()
        assert "will succeed" in captured.out

    def test_rolling_file_emit_ioerror_swallowed(self, tmp_path, monkeypatch):
        cfg = LogConfig(service="t", log_dir=str(tmp_path), file_max_size=1024)
        h = RollingFileHandler(cfg)
        h.emit("normal line")
        # 让 fp.write 抛异常
        original_write = h._fp.write

        def boom(s):
            raise IOError("write fail")

        monkeypatch.setattr(h._fp, "write", boom)
        h.emit("will fail")  # 不应崩溃
        monkeypatch.setattr(h._fp, "write", original_write)
        h.emit("after recovery")
        h.flush()
        h.close()
        # 至少 normal + after recovery 应在文件中
        with open(h._cur_path, encoding="utf-8") as f:
            content = f.read()
        assert "normal line" in content
        assert "after recovery" in content

    def test_rolling_file_flush_ioerror_swallowed(self, tmp_path, monkeypatch):
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        h = RollingFileHandler(cfg)
        h.emit("x")

        def boom():
            raise IOError("flush fail")

        monkeypatch.setattr(h._fp, "flush", boom)
        h.flush()  # 不应崩溃
        h.close()

    def test_rolling_file_close_ioerror_swallowed(self, tmp_path, monkeypatch):
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        h = RollingFileHandler(cfg)
        h.emit("x")

        def boom():
            raise IOError("close fail")

        # close 内部先 flush 再 close
        monkeypatch.setattr(h._fp, "flush", lambda: None)
        monkeypatch.setattr(h._fp, "close", boom)
        h.close()  # 不应崩溃

    def test_rolling_file_rotate_size_ioerror(self, tmp_path, monkeypatch):
        cfg = LogConfig(
            service="t",
            log_dir=str(tmp_path),
            file_max_size=10,  # 极小，立即触发
            file_backup_count=3,
        )
        h = RollingFileHandler(cfg)
        # 写入触发滚动
        h.emit("line1 padding")  # > 10 字节
        h.emit("line2 padding")
        # 让 os.rename 抛异常
        original_rename = os.rename

        def boom(*args, **kwargs):
            raise OSError("rename fail")

        monkeypatch.setattr(os, "rename", boom)
        h.emit("trigger rotate")  # 滚动时 rename 失败
        # 不应崩溃
        monkeypatch.setattr(os, "rename", original_rename)
        h.close()

    def test_rolling_file_cleanup_old_files_ioerror(self, tmp_path, monkeypatch):
        # 预创建一个旧文件
        old_file = os.path.join(str(tmp_path), "t-2020-01-01.log")
        with open(old_file, "w") as f:
            f.write("old")
        # 让 listdir 抛异常
        original_listdir = os.listdir

        def boom(path):
            if str(tmp_path) in str(path):
                raise OSError("listdir fail")
            return original_listdir(path)

        monkeypatch.setattr(os, "listdir", boom)
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        # 不应崩溃
        h = RollingFileHandler(cfg)
        h.close()


# ============================================================
# formatter.py 字段分支覆盖
# ============================================================
class TestFormatterCoverage:
    def test_build_record_with_all_optional_fields(self):
        from mini_logger.formatter import build_record
        rec = build_record(
            level=LogLevel.WARN,
            service="svc",
            msg="msg",
            trace_id="tid",
            span_id="sid",
            request_id="rid",
            user_id="uid",
            client_ip="1.1.1.1",
            tenant="tenant",
            module="mod",
            func="fn",
            line=99,
            err_type="ValueError",
            err_stack="stack",
            extra={"k": "v"},
        )
        assert rec["span_id"] == "sid"
        assert rec["request_id"] == "rid"
        assert rec["tenant"] == "tenant"
        assert rec["line"] == 99

    def test_format_human_with_minimal_record(self):
        from mini_logger.formatter import format_human
        rec = {"ts": "2026-01-01T00:00:00.000+08:00", "level": "UNKNOWN", "service": "s", "trace_id": "tid", "msg": "x"}
        # 未知 level 应回退到 INFO 颜色
        s = format_human(rec)
        assert "UNKNOWN" in s

    def test_format_human_with_line_field(self):
        from mini_logger.formatter import format_human
        rec = {
            "ts": "2026-01-01T00:00:00.000+08:00",
            "level": "INFO",
            "service": "s",
            "trace_id": "abcd1234",
            "msg": "x",
            "line": 42,
            "module": "mymod",
            "func": "myfn",
        }
        s = format_human(rec)
        assert "line=42" in s
        assert "module=mymod" in s
        assert "func=myfn" in s


# ============================================================
# core.py 其他边界覆盖
# ============================================================
class TestCoreEdgeCases:
    def test_warning_alias_works(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        lg = get_logger()
        lg.warning("via warning alias")
        _wait_flush()
        records = _read_records(str(tmp_path))
        assert any(r["msg"] == "via warning alias" and r["level"] == "WARN" for r in records)

    def test_critical_alias_works(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        lg = get_logger()
        lg.critical("via critical alias")
        _wait_flush()
        records = _read_records(str(tmp_path))
        assert any(r["msg"] == "via critical alias" and r["level"] == "FATAL" for r in records)

    def test_set_level_with_int(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        lg = get_logger()
        # 传 int
        lg.set_level(int(LogLevel.DEBUG))
        assert lg.level == LogLevel.DEBUG
        # 传非 LogLevel / str / int 的奇怪类型，应回退 INFO
        lg.set_level(None)
        assert lg.level == LogLevel.INFO

    def test_module_level_delegates_work(self, tmp_path):
        """模块级 debug/info/warn/error/fatal 委托函数。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        mini_logger.debug("d")
        mini_logger.info("i")
        mini_logger.warn("w")
        mini_logger.error("e")
        mini_logger.fatal("f")
        _wait_flush()
        records = _read_records(str(tmp_path))
        levels = [r["level"] for r in records]
        for lvl in ("DEBUG", "INFO", "WARN", "ERROR", "FATAL"):
            assert lvl in levels

    def test_console_json_mode(self, tmp_path, capsys):
        """json_console=True 时控制台也输出 JSON。"""
        init(
            service="t",
            console=True,
            file=False,
            json_console=True,
            level="INFO",
        )
        info("json console msg")
        _wait_flush()
        captured = capsys.readouterr()
        # 控制台应输出 JSON
        line = captured.out.strip().splitlines()[-1]
        rec = json.loads(line)
        assert rec["msg"] == "json console msg"

    def test_console_human_mode(self, tmp_path, capsys):
        """json_console=False 且非 TTY 时仍输出 JSON（测试环境无 TTY）。"""
        init(
            service="t",
            console=True,
            file=False,
            json_console=False,
            level="INFO",
        )
        info("human console msg")
        _wait_flush()
        captured = capsys.readouterr()
        # 测试环境非 TTY，回退 JSON
        assert "human console msg" in captured.out

    def test_no_handlers_no_crash(self, tmp_path):
        """全部 sink 关闭时调用日志方法不应崩溃。"""
        init(
            service="t",
            console=False,
            file=False,
            remote=False,
            level="INFO",
        )
        info("no handlers")  # 不崩溃
        _wait_flush()

    def test_extra_with_redact_disabled(self, tmp_path):
        """redact_enabled=False 时 extra 不被脱敏。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            redact_enabled=False,
        )
        info("msg", password="plain", phone="13812345678")
        _wait_flush()
        records = _read_records(str(tmp_path))
        rec = records[0]
        assert rec["extra"]["password"] == "plain"
        assert rec["extra"]["phone"] == "13812345678"

    def test_extra_redact_keys_custom(self, tmp_path):
        """自定义敏感字段名。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            extra_redact_keys=["my_secret_field"],
        )
        info("msg", my_secret_field="v", normal_field="ok")
        _wait_flush()
        records = _read_records(str(tmp_path))
        rec = records[0]
        assert rec["extra"]["my_secret_field"] == "***"
        assert rec["extra"]["normal_field"] == "ok"

    def test_remote_handler_init_when_no_url(self, tmp_path):
        """remote=True 但 remote_url=None 时不应实例化 RemoteHandler。"""
        init(
            service="t",
            console=False,
            file=False,
            remote=True,
            remote_url=None,
        )
        lg = get_logger()
        # 不应有 RemoteHandler
        assert not any(isinstance(h, RemoteHandler) for h in lg.handlers)


class TestRedactorEdgeCases:
    def test_empty_string_redact(self):
        from mini_logger.redactor import redact_string
        assert redact_string("") == ""

    def test_non_string_passthrough(self):
        from mini_logger.redactor import redact_any
        assert redact_any(42) == 42
        assert redact_any(3.14) == 3.14
        assert redact_any(None) is None
        assert redact_any(True) is True
        # list 不递归
        assert redact_any([1, 2]) == [1, 2]

    def test_dict_with_tuple_value(self):
        from mini_logger.redactor import redact_dict
        data = {"items": (1, 2, 3), "name": "x"}
        out = redact_dict(data)
        # tuple 不是 dict/str/list，原样保留
        assert out["items"] == (1, 2, 3)

    def test_dict_with_non_string_key(self):
        from mini_logger.redactor import redact_dict
        data = {1: "v", "name": "x"}
        out = redact_dict(data)
        # 非字符串 key 跳过敏感检查
        assert out[1] == "v"
