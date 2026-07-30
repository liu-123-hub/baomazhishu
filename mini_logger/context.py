"""mini_logger 上下文模块

基于 contextvars 实现链路追踪上下文：
- 协程（asyncio）内同一链路共享同一 trace_id
- 通过 asyncio.run_in_executor 派发到线程池的任务也能继承（contextvars 自动 propagate）
- bind_context() 返回 ContextToken，可显式 reset()（用于请求结束清理）

设计说明：contextvars 在创建 ContextVar 时设置 default=LogContext()，
确保 .get() 永不抛 LookupError；这样代码更简单且性能更好。
"""

from __future__ import annotations

import contextvars
import uuid
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class LogContext:
    """单次调用上下文。所有字段可选，按需注入。"""

    trace_id: str = ""
    span_id: str = ""
    request_id: str = ""
    user_id: str = ""
    client_ip: str = ""
    tenant: str = ""

    def ensure_trace_id(self) -> str:
        """trace_id 为空时自动生成（UUID4 去横线）。"""
        if not self.trace_id:
            self.trace_id = uuid.uuid4().hex
        return self.trace_id


class ContextToken:
    """bind_context 返回值。封装 contextvars.Token，提供 reset()。"""

    __slots__ = ("_var", "_token")

    def __init__(self, var: "contextvars.ContextVar", token) -> None:
        self._var = var
        self._token = token

    def reset(self) -> None:
        """还原到 bind_context 之前的状态。

        若 token 已失效（其他路径 set 过或已被 reset），忽略异常。
        兼容 Python 3.10（ValueError）与 3.13+（RuntimeError）。
        """
        try:
            self._var.reset(self._token)
        except (ValueError, RuntimeError, LookupError):
            # Token 已被其他路径重置或已使用：忽略
            pass


# contextvars 用于协程 / 线程池上下文隔离
_ctx: contextvars.ContextVar[LogContext] = contextvars.ContextVar(
    "mini_logger_ctx", default=LogContext()
)


def get_context() -> LogContext:
    """读取当前上下文。"""
    return _ctx.get()


def bind_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    client_ip: Optional[str] = None,
    tenant: Optional[str] = None,
) -> ContextToken:
    """注入上下文字段。返回 ContextToken，可调用 .reset() 恢复。

    典型用法（FastAPI 中间件）::

        token = mini_logger.bind_context(trace_id=req.headers.get("X-Trace-Id"))
        try:
            ...业务...
        finally:
            token.reset()
    """
    cur = _ctx.get()
    new = LogContext(
        trace_id=trace_id or cur.trace_id or uuid.uuid4().hex,
        span_id=span_id or cur.span_id or uuid.uuid4().hex[:8],
        request_id=request_id or cur.request_id,
        user_id=user_id or cur.user_id,
        client_ip=client_ip or cur.client_ip,
        tenant=tenant or cur.tenant,
    )
    token = _ctx.set(new)
    return ContextToken(_ctx, token)


def clear_context() -> None:
    """重置上下文为空白。一般在请求结束 / 任务退出时调用。"""
    _ctx.set(LogContext())
