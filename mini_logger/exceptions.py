"""mini_logger 异常栈自动捕获

提供装饰器 @catch_exception，用于业务函数内自动记录异常并重新抛出。
与 sys.excepthook 互补：
- excepthook 处理「未捕获」的崩溃
- @catch_exception 处理「被捕获但需要记录」的业务异常
"""

from __future__ import annotations

import functools
import sys
from typing import Any, Callable, Optional

from . import error as _error


def catch_exception(
    msg: str = "Exception raised",
    *,
    reraise: bool = True,
    level: str = "ERROR",
    **log_extra: Any,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """装饰器：捕获被装饰函数抛出的异常，记录后可选重新抛出。

    参数：
        msg: 日志消息
        reraise: 是否重新抛出异常（默认 True）
        level: 日志级别，ERROR / WARN / FATAL
        log_extra: 额外字段
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                # 在 except 内调用 error()，自动捕获栈
                log_method = _error
                log_method(msg, exc=e, func=fn.__name__, **log_extra)
                if reraise:
                    raise
                return None

        return wrapper

    return decorator
