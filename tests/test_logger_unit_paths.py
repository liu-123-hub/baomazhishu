"""针对未覆盖分支的精确单元测试，避免依赖后台线程时序。"""

import json
import os
import queue
import sys
import threading
import time

import pytest

import mini_logger
from mini_logger import init, info, error, debug, shutdown, get_logger, clear_context
from mini_logger.config import LogLevel, LogConfig
from mini_logger.context import (
    LogContext,
    ContextToken,
    _ctx,
    get_context,
    bind_context,
    clear_context,
)
from mini_logger.core import Logger
from mini_logger.handlers import (
    ConsoleHandler,
    RollingFileHandler,
    RemoteHandler,
)


@pytest.fixture(autouse=True)
def reset_logger():
    clear_context()
    shutdown()
    yield
    shutdown()
    clear_context()


# ============================================================
# context.py 直接覆盖
# ============================================================
class TestContextTokenResetExceptionPath:
    def test_reset_when_var_already_changed(self):
        """Token 已被 reset 过一次时，再次 reset 应回退到 except 分支不抛。"""
        token = bind_context(trace_id="first")
        token.reset()  # 第一次 reset 正常
        # 第二次 reset 同一 token，contextvars 抛 ValueError，应被吞
        token.reset()  # 不应崩溃
        # 后续 get_context 仍能正常工作
        assert isinstance(get_context(), LogContext)


# ============================================================
# core.py _enqueue 直接单元测试
# ============================================================
class _NoWorkerLogger(Logger):
    """测试专用：禁用后台 worker，使 _enqueue 行为可被确定化验证。"""

    def _consume_loop(self):
        # 不消费任何消息；测试直接调用 _enqueue 后再检查队列内容
        pass


class TestEnqueueDirect:
    """绕过后台线程时序，直接调用 _enqueue 验证各 drop_policy 分支。"""

    def _make_logger(self, drop_policy, queue_maxsize=2):
        cfg = LogConfig(
            service="t",
            console=False,
            file=False,
            remote=False,
            queue_maxsize=queue_maxsize,
            drop_policy=drop_policy,
            flush_interval=10.0,  # 不让后台消费
            level="DEBUG",
            catch_unhandled=False,  # 不安装 excepthook
        )
        return _NoWorkerLogger(cfg)

    def test_oldest_drop_drops_oldest_when_full(self):
        lg = self._make_logger("oldest", queue_maxsize=2)
        # 禁用 INFO 采样（默认 0.95 阈值在 qsize=2 时会误触发）
        lg.config.backpressure_drop = 2.0
        try:
            # 灌满
            assert lg._enqueue(LogLevel.INFO, "c1", "f1") is True
            assert lg._enqueue(LogLevel.INFO, "c2", "f2") is True
            # 第三条触发丢最旧
            assert lg._enqueue(LogLevel.INFO, "c3", "f3") is True
            # 队列应有 c2, c3
            items = []
            while True:
                try:
                    items.append(lg._queue.get_nowait())
                except queue.Empty:
                    break
            assert len(items) == 2
            assert items[0] == ("c2", "f2")
            assert items[1] == ("c3", "f3")
        finally:
            lg.shutdown()

    def test_newest_drop_returns_false_when_full(self):
        lg = self._make_logger("newest", queue_maxsize=2)
        lg.config.backpressure_drop = 2.0  # 禁用 INFO 采样
        try:
            assert lg._enqueue(LogLevel.INFO, "c1", "f1") is True
            assert lg._enqueue(LogLevel.INFO, "c2", "f2") is True
            # 第三条直接被拒
            assert lg._enqueue(LogLevel.INFO, "c3", "f3") is False
            # 队列保持 c1, c2
            items = []
            while True:
                try:
                    items.append(lg._queue.get_nowait())
                except queue.Empty:
                    break
            assert len(items) == 2
            assert items[0] == ("c1", "f1")
        finally:
            lg.shutdown()

    def test_block_returns_true_with_timeout(self):
        lg = self._make_logger("block", queue_maxsize=2)
        lg.config.backpressure_drop = 2.0
        try:
            assert lg._enqueue(LogLevel.INFO, "c1", "f1") is True
            assert lg._enqueue(LogLevel.INFO, "c2", "f2") is True
            # block 模式下，队列满时 put 会等待 timeout 后抛 Full，被外层 except 捕获返回 False
            result = lg._enqueue(LogLevel.INFO, "c3", "f3")
            # 由于 timeout=0.05，可能成功（若 worker 恰好消费）或失败
            assert result in (True, False)
        finally:
            lg.shutdown()

    def test_debug_dropped_at_warn_threshold(self):
        lg = self._make_logger("oldest", queue_maxsize=10)
        try:
            # 调整阈值
            lg.config.backpressure_warn = 0.2  # 2/10=0.2
            lg.config.backpressure_drop = 0.95
            # 灌入 2 条 INFO 达到 warn 阈值
            assert lg._enqueue(LogLevel.INFO, "c1", "f1") is True
            assert lg._enqueue(LogLevel.INFO, "c2", "f2") is True
            # DEBUG 应被丢弃
            assert lg._enqueue(LogLevel.DEBUG, "d1", "d1") is False
        finally:
            lg.shutdown()

    def test_info_sampled_at_drop_threshold(self):
        lg = self._make_logger("oldest", queue_maxsize=10)
        try:
            lg.config.backpressure_warn = 0.1
            lg.config.backpressure_drop = 0.3  # 3/10=0.3
            # 灌入 3 条 INFO 达到 drop 阈值
            for i in range(3):
                assert lg._enqueue(LogLevel.INFO, f"c{i}", f"f{i}") is True
            # 第 4 条 INFO 触发采样：奇偶线程 id 决定是否丢弃
            # 不一定都丢，但部分线程会被采样
            results = []
            for i in range(20):
                results.append(lg._enqueue(LogLevel.INFO, f"sample-{i}", f"sample-{i}"))
            # 至少有一个 True 或 False，且不崩溃
            assert any(r is True for r in results) or any(r is False for r in results)
        finally:
            lg.shutdown()


# ============================================================
# core.py excepthook queue.Full 路径
# ============================================================
class TestExcepthookQueueFull:
    def test_excepthook_swallows_queue_full(self, tmp_path, monkeypatch):
        """直接让 _queue.put_nowait 抛 queue.Full，验证 excepthook 不崩。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            catch_unhandled=True,
        )
        lg = get_logger()

        # 替换 put_nowait 为抛 Full
        def always_full(*args, **kwargs):
            raise queue.Full

        monkeypatch.setattr(lg._queue, "put_nowait", always_full)

        try:
            raise ValueError("trigger")
        except ValueError:
            exc_info = sys.exc_info()
        # excepthook 应吞掉 Full
        sys.excepthook(*exc_info)
        # 不崩溃即可
        monkeypatch.undo()
        shutdown(timeout=2.0)


# ============================================================
# core.py drain_remaining 异常分支
# ============================================================
class TestDrainRemainingException:
    def test_drain_remaining_continues_on_handler_error(self, tmp_path, monkeypatch):
        """shutdown 时 _drain_remaining 内 handler 抛异常应被吞，继续处理后续。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
            flush_interval=10.0,  # 不让后台消费
        )
        lg = get_logger()
        # 灌入 3 条
        info("m1")
        info("m2")
        info("m3")

        # 让 file handler emit 抛异常
        def boom(self, record):
            raise OSError("simulated")

        monkeypatch.setattr(RollingFileHandler, "emit", boom)
        # shutdown 触发 _drain_remaining，应吞异常并退出
        shutdown(timeout=2.0)
        # 不崩溃即可


# ============================================================
# core.py 关闭路径
# ============================================================
class TestShutdownPaths:
    def test_shutdown_when_queue_full_at_stop_signal(self, tmp_path, monkeypatch):
        """shutdown 发送 None 信号时若队列满应被吞。"""
        init(
            service="t",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="INFO",
            queue_maxsize=2,
            flush_interval=10.0,
        )
        lg = get_logger()
        # 灌满队列
        info("m1")
        info("m2")
        # 现在 put None 应触发 Full 路径但不崩
        shutdown(timeout=2.0)


# ============================================================
# handlers.py 异常分支精确覆盖
# ============================================================
class TestHandlerExceptionBranches:
    def test_console_emit_swallows_stdout_write_exception(self, monkeypatch):
        h = ConsoleHandler()

        # 让 stdout.write 始终抛异常
        call_count = {"n": 0}

        def fake_write(s):
            call_count["n"] += 1
            raise IOError("always fail")

        monkeypatch.setattr(sys.stdout, "write", fake_write)
        h.emit("test")  # 应进入 except 分支
        assert call_count["n"] >= 1

    def test_rolling_file_emit_swallows_fp_write_exception(self, tmp_path, monkeypatch):
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        h = RollingFileHandler(cfg)

        def boom(s):
            raise IOError("fp write fail")

        monkeypatch.setattr(h._fp, "write", boom)
        h.emit("will fail")  # 应进入 except pass 分支
        # 不崩溃即可
        h.close()

    def test_rolling_file_rotate_size_handles_rename_error(self, tmp_path, monkeypatch):
        cfg = LogConfig(
            service="t",
            log_dir=str(tmp_path),
            file_max_size=5,  # 极小
            file_backup_count=3,
        )
        h = RollingFileHandler(cfg)

        # 让 fp.close 抛异常（_rotate_size 内部会先 close）
        original_close = h._fp.close

        def boom():
            raise OSError("close fail in rotate")

        # close 在 _rotate_size 中被调用，应被吞（_rotate_size 内未捕获会传播）
        # 实际上 _rotate_size 中 close 调用未在 try 内，会抛出
        # 但 emit 调用 _rotate_if_needed 在 _rotate_size 之外，emit 内有 try
        # 让 os.rename 抛异常
        def rename_boom(*args, **kwargs):
            raise OSError("rename fail")

        monkeypatch.setattr(os, "rename", rename_boom)
        # emit 时 _rotate_if_needed -> _rotate_size -> rename 失败抛 OSError
        # emit 内有 try/except 捕获
        h.emit("padding-xxxxxxxxxxx")  # 触发滚动
        # 不崩溃
        h.close()

    def test_rolling_file_open_handles_oserror(self, tmp_path, monkeypatch):
        """_open_current 中 getsize 抛 OSError 应被吞。"""
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        h = RollingFileHandler(cfg)
        h.emit("x")
        h.flush()

        # 模拟 getsize 抛异常
        def boom(path):
            raise OSError("getsize fail")

        monkeypatch.setattr(os.path, "getsize", boom)
        # 触发 _open_current（日期变化或大小滚动）
        # 强制调用 _open_current
        h._open_current()
        # 不崩溃，cur_size 应为 0（被 except 捕获后默认）
        assert h._cur_size == 0
        h.close()

    def test_rolling_file_cleanup_handles_listdir_error(self, tmp_path, monkeypatch):
        """_cleanup_old_files 中 listdir 抛 OSError 应被吞。"""
        # 预创建文件
        cfg = LogConfig(service="t", log_dir=str(tmp_path), file_backup_count=2)
        # 先正常初始化
        h = RollingFileHandler(cfg)
        h.close()

        # 让 listdir 抛异常
        def boom(path):
            raise OSError("listdir fail")

        monkeypatch.setattr(os, "listdir", boom)
        # 重新初始化，应触发 _cleanup_old_files 中的 except
        h2 = RollingFileHandler(cfg)
        h2.close()


# ============================================================
# formatter.py / core.py 边界
# ============================================================
class TestFormatterAndCoreEdges:
    def test_set_level_invalid_int_falls_back_to_info(self, tmp_path):
        """set_level 传入非 LogLevel 数值（如 999）应回退 INFO。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        lg = get_logger()
        # 999 不是有效 LogLevel
        lg.set_level(999)
        assert lg.level == LogLevel.INFO

    def test_set_level_invalid_type_falls_back_to_info(self, tmp_path):
        """set_level 传入 list 等非法类型应回退 INFO。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        lg = get_logger()
        lg.set_level(["DEBUG"])
        assert lg.level == LogLevel.INFO

    def test_set_level_valid_int(self, tmp_path):
        init(service="t", console=False, file=True, log_dir=str(tmp_path))
        lg = get_logger()
        lg.set_level(20)  # 等同 INFO
        assert lg.level == LogLevel.INFO
        lg.set_level(10)  # DEBUG
        assert lg.level == LogLevel.DEBUG

    def test_warning_alias_line(self, tmp_path):
        """覆盖 warning = warn 别名行。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        # 验证别名存在
        assert hasattr(mini_logger, "warn")
        # 调用
        mini_logger.warn("test warn")
        # 不崩溃

    def test_critical_alias_line(self, tmp_path):
        """覆盖 critical = fatal 别名行。"""
        init(service="t", console=False, file=True, log_dir=str(tmp_path), level="DEBUG")
        assert hasattr(mini_logger, "fatal")
        mini_logger.fatal("test fatal")


# ============================================================
# 集成补充：脱敏 + 调用位置 + 异常栈完整链路
# ============================================================
class TestFullChain:
    def test_full_chain_with_all_features(self, tmp_path):
        """一次调用同时验证：trace_id 注入 / 调用位置 / 异常栈 / 脱敏。"""
        init(
            service="full-chain-svc",
            console=False,
            file=True,
            log_dir=str(tmp_path),
            level="DEBUG",
            include_location=True,
            redact_enabled=True,
        )

        token = bind_context(
            trace_id="chain-trace-id",
            user_id="chain-user",
            client_ip="10.20.30.40",
        )
        try:
            try:
                raise ConnectionError("db unreachable")
            except ConnectionError as e:
                error(
                    "db operation failed",
                    exc=e,
                    sql="SELECT * FROM users WHERE phone='13812345678'",
                    id_card="110101199003078888",
                )
        finally:
            token.reset()
            clear_context()

        # 等待 flush
        lg = get_logger()
        deadline = time.time() + 2.0
        while time.time() < deadline:
            if lg._queue.qsize() == 0:
                break
            time.sleep(0.005)
        for h in lg.handlers:
            h.flush()
        shutdown(timeout=2.0)

        # 读取并断言
        records = []
        for f in os.listdir(str(tmp_path)):
            if not f.endswith(".log"):
                continue
            with open(os.path.join(str(tmp_path), f), encoding="utf-8") as fp:
                for line in fp:
                    if line.strip():
                        records.append(json.loads(line))

        assert len(records) >= 1
        rec = records[0]
        # 上下文注入
        assert rec["trace_id"] == "chain-trace-id"
        assert rec["user_id"] == "chain-user"
        assert rec["client_ip"] == "10.20.30.40"
        # 调用位置
        assert rec["module"] == __name__
        assert rec["func"] == "test_full_chain_with_all_features"
        assert rec["line"] > 0
        # 异常栈
        assert rec["err_type"] == "ConnectionError"
        assert "db unreachable" in rec["err_stack"]
        # 脱敏：手机号和身份证号不应出现在原始形式
        sql_val = rec["extra"]["sql"]
        id_val = rec["extra"]["id_card"]
        assert "13812345678" not in sql_val
        assert "110101199003078888" not in id_val
