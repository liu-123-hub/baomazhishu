"""mini_logger —— 极简全链路日志系统

唯一对外入口：
    from mini_logger import init, debug, info, warn, error, fatal, get_logger, set_level, bind_context

设计目标：
1. 1 行初始化：mini_logger.init(service="xxx")
2. 仅暴露 5 个日志级别方法 + 辅助方法
3. 自动注入链路追踪 ID / 服务标识 / 时间戳 / 调用位置
4. 内置敏感信息脱敏、异步落盘、滚动切割、背压采样、动态级别、异常栈捕获
5. 零冗余依赖（仅 Python 3.10+ 标准库）
"""

from .core import (
    Logger,
    get_logger,
    init,
    debug,
    info,
    warn,
    error,
    fatal,
    set_level,
    bind_context,
    clear_context,
    shutdown,
)
from .config import LogLevel, LogConfig
from .exceptions import catch_exception

__all__ = [
    # 核心 API
    "init",
    "debug",
    "info",
    "warn",
    "error",
    "fatal",
    "get_logger",
    "set_level",
    "bind_context",
    "clear_context",
    "shutdown",
    # 异常装饰器
    "catch_exception",
    # 类型
    "Logger",
    "LogLevel",
    "LogConfig",
    "__version__",
]

__version__ = "1.0.0"
