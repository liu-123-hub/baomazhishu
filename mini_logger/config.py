"""mini_logger 配置模块

定义日志级别枚举与配置数据类。所有配置项均提供合理默认值，
开发者仅需 `init(service="xxx")` 一行即可启动，复杂场景再按需覆盖。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class LogLevel(IntEnum):
    """日志级别（数值越小越严重，便于阈值比较）。

    FATAL < ERROR < WARN < INFO < DEBUG
    """

    FATAL = 50
    ERROR = 40
    WARN = 30
    INFO = 20
    DEBUG = 10

    @classmethod
    def from_str(cls, name: str) -> "LogLevel":
        """字符串 -> LogLevel，大小写不敏感；非法值回退 INFO。"""
        try:
            return cls[name.upper()]
        except KeyError:
            return cls.INFO


@dataclass
class LogConfig:
    """日志系统配置。

    所有字段均可通过 init() 关键字参数覆盖，避免在多处维护配置。
    """

    # === 必填 ===
    service: str = "default-service"
    env: str = "dev"

    # === 级别 ===
    level: LogLevel = LogLevel.INFO

    # === 输出开关 ===
    console: bool = True
    file: bool = True
    remote: bool = False

    # === 文件滚动策略 ===
    log_dir: str = "logs"
    file_max_size: int = 10 * 1024 * 1024  # 10MB
    file_backup_count: int = 30           # 保留 30 天

    # === 远端配置 ===
    remote_url: Optional[str] = None
    remote_timeout: float = 2.0
    remote_batch_size: int = 50

    # === 异步与背压 ===
    queue_maxsize: int = 65536
    flush_interval: float = 0.2           # 后台线程 flush 间隔（秒）
    max_msg_bytes: int = 64 * 1024        # 单条日志最大字节，超出截断
    backpressure_warn: float = 0.80       # 队列水位告警阈值
    backpressure_drop: float = 0.95       # 队列采样阈值
    drop_policy: str = "oldest"           # oldest | newest | block

    # === 格式 ===
    json_console: bool = False            # True: 控制台也输出 JSON；False: 人类可读
    include_location: bool = True         # 是否记录 module/func/line
    timezone: str = "Asia/Shanghai"       # UTC+8 默认

    # === 脱敏 ===
    redact_enabled: bool = True
    extra_redact_keys: List[str] = field(default_factory=list)

    # === 异常捕获 ===
    catch_unhandled: bool = True          # 自动安装 sys.excepthook 捕获未处理异常

    def __post_init__(self) -> None:
        # 兼容字符串级别（init 时方便传入）
        if isinstance(self.level, str):
            self.level = LogLevel.from_str(self.level)
        # 自动创建日志目录
        if self.file:
            os.makedirs(self.log_dir, exist_ok=True)
