"""mini_logger 核心 Logger

特性：
- 1 行 init() 完成 5 个级别方法暴露
- 后台单线程消费 queue，主线程 emit 仅入队（O(1) 内存拷贝）
- 背压：队列水位 > warn 阈值 → 丢 DEBUG；> drop 阈值 → 采样 50% INFO；满则按 drop_policy
- 动态级别：set_level() 原子切换，无需重启
- 异常栈自动捕获：fatal/exception 自动写入完整 traceback
- 资源控制：单条消息超过 max_msg_bytes 截断
- 优雅退出：shutdown() flush 所有 handler
"""

from __future__ import annotations

import inspect
import os
import queue
import sys
import threading
import traceback
import uuid
from typing import Any, Dict, Optional

from .config import LogConfig, LogLevel
from .context import get_context, bind_context as _bind_context, clear_context as _clear_context
from .formatter import build_record, format_record, supports_color
from .handlers import BaseHandler, ConsoleHandler, RollingFileHandler, RemoteHandler
from .redactor import redact_any

# 全局单例
_logger: Optional["Logger"] = None
_init_lock = threading.Lock()


class Logger:
    """日志器主体。通常通过 init() 创建全局单例，通过 get_logger() 获取。"""

    def __init__(self, config: LogConfig) -> None:
        self.config = config
        self._level = int(config.level)  # 原子读写：int 读写是 Python 原子操作
        self._level_lock = threading.Lock()

        # 输出 sink
        self.handlers: list[BaseHandler] = []
        if config.console:
            as_json = config.json_console
            self.handlers.append(ConsoleHandler(as_json=as_json))
        if config.file:
            self.handlers.append(RollingFileHandler(config))
        if config.remote and config.remote_url:
            self.handlers.append(RemoteHandler(config))

        # 异步队列与后台线程
        self._queue: "queue.Queue[Optional[str]]" = queue.Queue(maxsize=config.queue_maxsize)
        self._stop = threading.Event()
        self._worker = threading.Thread(
            target=self._consume_loop, name="mini-logger-worker", daemon=True
        )
        self._dropped_count = 0
        self._lock_drop = threading.Lock()

        # 启动后台线程
        self._worker.start()

        # 异常钩子（在所有 handler 都就绪后安装，避免初始化阶段的异常被吞）
        if config.catch_unhandled:
            self._install_excepthook()

    # === 级别控制 ===
    @property
    def level(self) -> LogLevel:
        with self._level_lock:
            return LogLevel(self._level)

    def set_level(self, level) -> None:
        """动态调整日志级别，无需重启。

        接受 LogLevel / str / int；非法值回退 INFO。
        """
        if isinstance(level, LogLevel):
            new_level = level
        elif isinstance(level, str):
            new_level = LogLevel.from_str(level)
        elif isinstance(level, int):
            try:
                new_level = LogLevel(level)
            except ValueError:
                new_level = LogLevel.INFO
        else:
            new_level = LogLevel.INFO
        with self._level_lock:
            self._level = int(new_level)

    def _is_enabled(self, level: LogLevel) -> bool:
        return int(level) >= self._level

    # === 公开 API ===
    def debug(self, msg: str, **extra: Any) -> None:
        self._log(LogLevel.DEBUG, msg, extra=extra)

    def info(self, msg: str, **extra: Any) -> None:
        self._log(LogLevel.INFO, msg, extra=extra)

    def warn(self, msg: str, **extra: Any) -> None:
        self._log(LogLevel.WARN, msg, extra=extra)

    warning = warn  # 别名

    def error(self, msg: str, exc: Optional[BaseException] = None, **extra: Any) -> None:
        self._log(LogLevel.ERROR, msg, exc=exc, extra=extra)

    def fatal(self, msg: str, exc: Optional[BaseException] = None, **extra: Any) -> None:
        self._log(LogLevel.FATAL, msg, exc=exc, extra=extra)

    critical = fatal  # 别名

    def exception(self, msg: str = "Unhandled exception", **extra: Any) -> None:
        """在 except 块内调用：自动捕获当前异常栈。"""
        exc_info = sys.exc_info()
        exc = exc_info[1] if exc_info and exc_info[0] is not None else None
        self._log(LogLevel.ERROR, msg, exc=exc, extra=extra)

    # === 内部实现 ===
    def _log(
        self,
        level: LogLevel,
        msg: str,
        exc: Optional[BaseException] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._is_enabled(level):
            return

        # 1. 提取调用位置
        module = func = ""
        line = 0
        if self.config.include_location:
            frame = inspect.currentframe()
            # _log -> debug/info/... -> 业务调用：跳过 3 层
            try:
                # 业务调用方：往上回溯到非 mini_logger 的帧
                caller = None
                while frame is not None:
                    f = frame.f_back
                    if f is None:
                        break
                    fname = f.f_globals.get("__name__", "")
                    if not fname.startswith("mini_logger"):
                        caller = f
                        break
                    frame = f
                if caller is not None:
                    module = caller.f_globals.get("__name__", "")
                    func = caller.f_code.co_name
                    line = caller.f_lineno
            finally:
                del frame  # 避免引用环

        # 2. 异常栈
        err_type = err_stack = ""
        if exc is not None:
            err_type = type(exc).__name__
            err_stack = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            )
        elif sys.exc_info()[1] is not None:
            # 调用方在 except 块内未显式传 exc：自动捕获
            e = sys.exc_info()[1]
            err_type = type(e).__name__
            err_stack = "".join(
                traceback.format_exception(type(e), e, e.__traceback__)
            )

        # 3. 上下文
        ctx = get_context()
        ctx.ensure_trace_id()

        # 4. 构造 record
        record = build_record(
            level=level,
            service=self.config.service,
            msg=msg,
            trace_id=ctx.trace_id,
            span_id=ctx.span_id,
            request_id=ctx.request_id,
            user_id=ctx.user_id,
            client_ip=ctx.client_ip,
            tenant=ctx.tenant,
            module=module,
            func=func,
            line=line,
            err_type=err_type,
            err_stack=err_stack,
            extra=extra or {},
        )

        # 5. 脱敏
        if self.config.redact_enabled:
            record = redact_any(record, extra_keys=self.config.extra_redact_keys)

        # 6. 格式化
        as_json = self.config.json_console or not supports_color()
        # 文件 sink 始终 JSON；控制台可人类可读
        line_str = format_record(record, as_json=True)  # 文件用 JSON
        console_str = format_record(record, as_json=self.config.json_console or not supports_color())

        # 7. 截断超长消息
        max_b = self.config.max_msg_bytes
        if len(line_str.encode("utf-8")) > max_b:
            line_str = line_str[: max_b - 64] + "...<truncated>"
        if len(console_str.encode("utf-8")) > max_b:
            console_str = console_str[: max_b - 64] + "...<truncated>"

        # 8. 背压决策
        if not self._enqueue(level, console_str, line_str):
            with self._lock_drop:
                self._dropped_count += 1

    def _enqueue(self, level: LogLevel, console_str: str, file_str: str) -> bool:
        """根据队列水位决定是否入队。返回 True 表示成功。"""
        qsize = self._queue.qsize()
        capacity = self.config.queue_maxsize
        # 高水位：丢 DEBUG
        if qsize >= capacity * self.config.backpressure_warn and level == LogLevel.DEBUG:
            return False
        # 极高水位：采样 50% INFO
        if qsize >= capacity * self.config.backpressure_drop and level == LogLevel.INFO:
            # 简单确定性采样：基于线程 id 奇偶
            if threading.get_ident() % 2 == 0:
                return False
        try:
            if self.config.drop_policy == "block":
                self._queue.put((console_str, file_str), timeout=0.05)
            elif self.config.drop_policy == "newest":
                try:
                    self._queue.put_nowait((console_str, file_str))
                except queue.Full:
                    return False
            else:  # oldest
                try:
                    self._queue.put_nowait((console_str, file_str))
                except queue.Full:
                    # 丢弃最旧一条
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                    try:
                        self._queue.put_nowait((console_str, file_str))
                    except queue.Full:
                        return False
            return True
        except queue.Full:
            return False

    def _consume_loop(self) -> None:
        """后台线程：从队列消费，分发到各 handler。"""
        # 每条记录携带 (console_str, file_str) 元组
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=self.config.flush_interval)
            except queue.Empty:
                # 空闲时主动 flush 文件 handler
                for h in self.handlers:
                    try:
                        h.flush()
                    except Exception:
                        pass
                continue
            if item is None:
                # shutdown 信号
                break
            console_str, file_str = item
            for h in self.handlers:
                # 简单分发：ConsoleHandler 收 console_str；其他收 file_str
                # handler 异常不应让 worker 崩溃
                try:
                    if isinstance(h, ConsoleHandler):
                        h.emit(console_str)
                    else:
                        h.emit(file_str)
                except Exception:
                    pass
        # 退出前 drain 剩余
        self._drain_remaining()
        for h in self.handlers:
            try:
                h.flush()
                h.close()
            except Exception:
                pass

    def _drain_remaining(self) -> None:
        """退出时把队列剩余记录全部输出。"""
        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                continue
            console_str, file_str = item
            for h in self.handlers:
                try:
                    if isinstance(h, ConsoleHandler):
                        h.emit(console_str)
                    else:
                        h.emit(file_str)
                except Exception:
                    pass

    def _install_excepthook(self) -> None:
        """安装 sys.excepthook，捕获未处理异常并以 FATAL 记录。"""
        self._original_excepthook = sys.excepthook

        def hook(exc_type, exc_value, exc_tb):
            try:
                if exc_value is not None:
                    err_type = exc_type.__name__
                    err_stack = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
                    ctx = get_context()
                    ctx.ensure_trace_id()
                    record = build_record(
                        level=LogLevel.FATAL,
                        service=self.config.service,
                        msg=f"Unhandled {err_type}: {exc_value}",
                        trace_id=ctx.trace_id,
                        span_id=ctx.span_id,
                        request_id=ctx.request_id,
                        user_id=ctx.user_id,
                        client_ip=ctx.client_ip,
                        tenant=ctx.tenant,
                        module="",
                        func="",
                        line=0,
                        err_type=err_type,
                        err_stack=err_stack,
                        extra={},
                    )
                    if self.config.redact_enabled:
                        record = redact_any(record, extra_keys=self.config.extra_redact_keys)
                    line_str = format_record(record, as_json=True)
                    console_str = format_record(
                        record, as_json=self.config.json_console or not supports_color()
                    )
                    try:
                        self._queue.put_nowait((console_str, line_str))
                    except queue.Full:
                        pass
            finally:
                # 调用原始 hook，保证默认行为（如 stderr 打印）保留
                self._original_excepthook(exc_type, exc_value, exc_tb)

        sys.excepthook = hook

    def _restore_excepthook(self) -> None:
        """还原 sys.excepthook。"""
        if getattr(self, "_original_excepthook", None) is not None:
            sys.excepthook = self._original_excepthook
            self._original_excepthook = None

    def shutdown(self, timeout: float = 2.0) -> None:
        """优雅关闭：发送停止信号，等待后台线程 drain 完毕。"""
        if self._stop.is_set():
            return
        # 还原 excepthook，避免关闭后回调访问已释放的 handler
        self._restore_excepthook()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        self._worker.join(timeout=timeout)
        self._stop.set()


# ===========================
# 模块级公开 API
# ===========================
def init(**kwargs) -> Logger:
    """初始化全局日志器。一行即可：mini_logger.init(service="xxx")

    支持的关键字参数同 LogConfig。常见：
        service: 服务标识（必填建议）
        level: LogLevel 或字符串（DEBUG/INFO/WARN/ERROR/FATAL）
        console/file/remote: bool，是否启用对应 sink
        log_dir: 文件目录，默认 logs
        json_console: 控制台是否输出 JSON，默认 False（人类可读）
    """
    global _logger
    with _init_lock:
        if _logger is not None:
            _logger.shutdown()
        config = LogConfig(**kwargs)
        _logger = Logger(config)
        return _logger


def get_logger() -> Logger:
    """获取全局 Logger 单例。未 init 时返回默认配置的 logger。"""
    global _logger
    if _logger is None:
        with _init_lock:
            if _logger is None:
                _logger = Logger(LogConfig())
    return _logger


def _delegate(method: str):
    """生成代理函数：module.debug(...) -> get_logger().debug(...)"""

    def _wrapper(msg: str, **kwargs: Any) -> None:
        logger = _logger or get_logger()
        getattr(logger, method)(msg, **kwargs)

    _wrapper.__name__ = method
    return _wrapper


# 5 个核心 API
debug = _delegate("debug")
info = _delegate("info")
warn = _delegate("warn")
error = _delegate("error")
fatal = _delegate("fatal")


def set_level(level) -> None:
    """动态调整全局日志级别。"""
    get_logger().set_level(level)


def bind_context(*args, **kwargs):
    """注入链路上下文（trace_id/user_id/client_ip 等）。返回 token。"""
    return _bind_context(*args, **kwargs)


def clear_context() -> None:
    """清空当前上下文。"""
    _clear_context()


def shutdown(timeout: float = 2.0) -> None:
    """关闭全局 Logger（程序退出时调用）。"""
    global _logger
    if _logger is not None:
        _logger.shutdown(timeout=timeout)
        _logger = None
