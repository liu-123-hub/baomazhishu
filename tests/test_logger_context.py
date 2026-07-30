"""上下文模块测试"""

import asyncio
import threading

import pytest

from mini_logger.context import (
    LogContext,
    ContextToken,
    get_context,
    bind_context,
    clear_context,
    _ctx,
)


class TestLogContext:
    def test_ensure_trace_id_generates(self):
        ctx = LogContext()
        tid = ctx.ensure_trace_id()
        assert tid and len(tid) == 32  # uuid4.hex 长度
        assert ctx.trace_id == tid  # 第二次返回相同值
        assert ctx.ensure_trace_id() == tid

    def test_ensure_trace_id_keeps_existing(self):
        ctx = LogContext(trace_id="predefined-id")
        assert ctx.ensure_trace_id() == "predefined-id"


class TestGetContext:
    def test_default_returns_blank(self):
        clear_context()
        ctx = get_context()
        assert isinstance(ctx, LogContext)

    def test_thread_isolation(self):
        # 子线程上下文不应影响主线程
        clear_context()
        bind_context(trace_id="main-tid", user_id="u1")

        captured = {}

        def worker():
            captured["ctx"] = get_context()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # 主线程 ctx 仍存在
        main_ctx = get_context()
        assert main_ctx.trace_id == "main-tid"
        # 子线程独立 ctx（默认空，因 threading.Thread 不复制 contextvars）
        assert captured["ctx"].trace_id == ""


class TestBindContext:
    def test_bind_and_read(self):
        clear_context()
        token = bind_context(
            trace_id="trace-123",
            user_id="user-abc",
            client_ip="10.0.0.1",
        )
        ctx = get_context()
        assert ctx.trace_id == "trace-123"
        assert ctx.user_id == "user-abc"
        assert ctx.client_ip == "10.0.0.1"
        # span_id / request_id 默认生成
        assert ctx.span_id != ""
        token.reset()

    def test_bind_auto_generates_trace_id(self):
        clear_context()
        token = bind_context()
        ctx = get_context()
        assert ctx.trace_id and len(ctx.trace_id) == 32
        token.reset()

    def test_bind_preset_field_inheritance(self):
        clear_context()
        t1 = bind_context(trace_id="tid-1", user_id="u1")
        # 二次 bind 不指定 trace_id 时应继承前一次
        t2 = bind_context(span_id="span-2")
        ctx = get_context()
        assert ctx.trace_id == "tid-1"
        assert ctx.user_id == "u1"
        assert ctx.span_id == "span-2"
        t2.reset()
        t1.reset()

    def test_clear_context(self):
        bind_context(trace_id="abc", user_id="u1")
        clear_context()
        ctx = get_context()
        assert ctx.trace_id == ""
        assert ctx.user_id == ""

    def test_token_reset_when_invalidated(self):
        """token 已被 reset 过一次后，再次 reset 不抛异常。"""
        clear_context()
        token = bind_context(trace_id="first")
        token.reset()  # 第一次 reset 正常
        # 第二次 reset 同一 token，contextvars 抛 ValueError，应被吞
        token.reset()  # 不应崩溃
        # 后续 get_context 仍正常
        assert isinstance(get_context(), LogContext)


class TestAsyncContext:
    @pytest.mark.asyncio
    async def test_async_isolation(self):
        """协程间上下文应隔离。"""
        clear_context()
        bind_context(trace_id="outer")

        async def child(tid):
            bind_context(trace_id=tid)
            await asyncio.sleep(0.01)
            return get_context().trace_id

        # 并发执行两个协程，各自设置不同 trace_id
        r1, r2 = await asyncio.gather(child("a"), child("b"))
        assert r1 == "a"
        assert r2 == "b"
        # 外层 ctx 仍是 outer
        assert get_context().trace_id == "outer"
        clear_context()
