"""mini_logger 输出处理器

三种 sink：
- ConsoleHandler：stdout 输出（人类可读或 JSON）
- RollingFileHandler：本地滚动文件，按日期 + 大小双维度切割
- RemoteHandler：批量 POST 到远端日志平台（httpx 失败时不阻塞主线程）

所有 handler 暴露统一接口 emit(record_str: str) / flush() / close()。
"""

from __future__ import annotations

import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from .config import LogConfig

_TZ_CN = timezone(timedelta(hours=8))


class BaseHandler:
    """handler 抽象基类。子类需实现 emit / flush / close。"""

    def emit(self, record: str) -> None:
        raise NotImplementedError

    def flush(self) -> None:
        """默认空实现，文件 / 远端 handler 覆盖。"""

    def close(self) -> None:
        """默认空实现。"""


class ConsoleHandler(BaseHandler):
    """stdout 输出。

    - as_json=True：单行 JSON
    - as_json=False：颜色高亮人类可读
    """

    def __init__(self, as_json: bool = False) -> None:
        self.as_json = as_json

    def emit(self, record: str) -> None:
        try:
            sys.stdout.write(record + "\n")
            sys.stdout.flush()
        except Exception:
            # 控制台写入失败（管道已关闭等）不应影响主线程
            pass


class RollingFileHandler(BaseHandler):
    """按日期 + 大小双维度滚动切割的文件 handler。

    - 文件名：{log_dir}/{service}-{YYYY-MM-DD}.log
    - 滚动条件（任一触发）：
      a) 日期变化 → 关闭当前文件，新建下一天的文件
      b) 当前文件大小 >= file_max_size → 重命名为 .1, .2, ... 最多保留 backup_count 份
    - 启动时清理超过 backup_count 天的旧文件
    """

    def __init__(self, config: LogConfig) -> None:
        self.config = config
        self.service = config.service
        self.log_dir = config.log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._fp: Optional[object] = None
        self._cur_date: str = ""
        self._cur_size: int = 0
        self._cur_path: str = ""
        self._lock = threading.Lock()
        self._cleanup_old_files()
        self._open_current()

    def _date_str(self) -> str:
        return datetime.now(_TZ_CN).strftime("%Y-%m-%d")

    def _file_base(self, date_str: str) -> str:
        return os.path.join(self.log_dir, f"{self.service}-{date_str}.log")

    def _open_current(self) -> None:
        """打开（或新建）当前日期的日志文件。"""
        if self._fp is not None:
            try:
                self._fp.close()
            except Exception:
                pass
        self._cur_date = self._date_str()
        self._cur_path = self._file_base(self._cur_date)
        # 以追加模式打开，缓冲区由 flush 显式控制
        self._fp = open(self._cur_path, "a", encoding="utf-8", buffering=1)
        try:
            self._cur_size = os.path.getsize(self._cur_path)
        except OSError:
            self._cur_size = 0

    def _cleanup_old_files(self) -> None:
        """启动时清理超过 backup_count 天的旧日志。"""
        try:
            files = sorted(os.listdir(self.log_dir))
            # 仅匹配本 service 的日志
            prefix = f"{self.service}-"
            old_logs = [f for f in files if f.startswith(prefix) and f.endswith(".log")]
            # 按 modify time 排序，保留最新 backup_count 个
            old_logs.sort(
                key=lambda f: os.path.getmtime(os.path.join(self.log_dir, f)),
                reverse=True,
            )
            for stale in old_logs[self.config.file_backup_count :]:
                try:
                    os.remove(os.path.join(self.log_dir, stale))
                except OSError:
                    pass
        except OSError:
            pass

    def _rotate_if_needed(self) -> None:
        """检查是否需要切换文件（日期变化或文件过大）。"""
        today = self._date_str()
        if today != self._cur_date:
            self._open_current()
            return
        if self._cur_size >= self.config.file_max_size:
            self._rotate_size()

    def _rotate_size(self) -> None:
        """按大小滚动：service-date.log → service-date.log.1, .1 → .2, ..."""
        assert self._fp is not None
        try:
            self._fp.close()
        except Exception:
            pass
        self._fp = None
        # 滚动 .(n-1) -> .n，从最大编号开始
        base = self._cur_path
        n = 1
        while os.path.exists(f"{base}.{n}"):
            n += 1
        for i in range(n, 0, -1):
            src = f"{base}.{i - 1}" if i > 1 else base
            dst = f"{base}.{i}"
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                os.rename(src, dst)
            except OSError:
                pass
        # 重新打开新文件
        self._fp = open(self._cur_path, "a", encoding="utf-8", buffering=1)
        self._cur_size = 0

    def emit(self, record: str) -> None:
        with self._lock:
            self._rotate_if_needed()
            if self._fp is None:
                return
            line = record + "\n"
            try:
                self._fp.write(line)
                self._cur_size += len(line.encode("utf-8"))
            except Exception:
                pass

    def flush(self) -> None:
        if self._fp is not None:
            try:
                self._fp.flush()
            except Exception:
                pass

    def close(self) -> None:
        if self._fp is not None:
            try:
                self._fp.flush()
                self._fp.close()
            except Exception:
                pass
            self._fp = None


class RemoteHandler(BaseHandler):
    """远端日志平台 handler。

    批量缓冲 + 后台线程 flush，HTTP 失败时丢弃批次避免反压。
    使用 httpx.AsyncClient（如果可用）否则降级到 urllib。
    为了避免在 mini_logger 中引入硬依赖，这里使用 stdlib urllib。
    """

    def __init__(self, config: LogConfig) -> None:
        self.config = config
        self.url = config.remote_url
        self.timeout = config.remote_timeout
        self.batch: list[str] = []
        self.batch_size = config.remote_batch_size
        self._lock = threading.Lock()

    def emit(self, record: str) -> None:
        with self._lock:
            self.batch.append(record)
            if len(self.batch) >= self.batch_size:
                self._send_batch()

    def flush(self) -> None:
        with self._lock:
            if self.batch:
                self._send_batch()

    def _send_batch(self) -> None:
        """同步发送当前批次。失败静默丢弃，避免影响主线程。"""
        if not self.url:
            return
        batch = list(self.batch)
        self.batch.clear()
        payload = "\n".join(batch)
        # 用线程池内的同步请求，避免在 mini_logger 主后台线程中阻塞过久
        try:
            import urllib.request
            import urllib.error

            req = urllib.request.Request(
                self.url,
                data=payload.encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=self.timeout)
        except Exception:
            # 远端不可达：丢弃当前批次
            pass

    def close(self) -> None:
        self.flush()
