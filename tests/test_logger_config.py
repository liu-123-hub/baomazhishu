"""LogConfig / LogLevel 单元测试"""

import os
import tempfile

import pytest

from mini_logger.config import LogLevel, LogConfig


class TestLogLevel:
    def test_from_str_upper(self):
        assert LogLevel.from_str("DEBUG") == LogLevel.DEBUG
        assert LogLevel.from_str("INFO") == LogLevel.INFO
        assert LogLevel.from_str("WARN") == LogLevel.WARN
        assert LogLevel.from_str("ERROR") == LogLevel.ERROR
        assert LogLevel.from_str("FATAL") == LogLevel.FATAL

    def test_from_str_lower(self):
        assert LogLevel.from_str("debug") == LogLevel.DEBUG
        assert LogLevel.from_str("info") == LogLevel.INFO

    def test_from_str_invalid_fallback_info(self):
        assert LogLevel.from_str("xxx") == LogLevel.INFO
        assert LogLevel.from_str("") == LogLevel.INFO

    def test_value_order(self):
        # 数值越小越严重
        assert LogLevel.FATAL > LogLevel.ERROR > LogLevel.WARN > LogLevel.INFO > LogLevel.DEBUG
        assert int(LogLevel.DEBUG) == 10
        assert int(LogLevel.FATAL) == 50


class TestLogConfig:
    def test_default_values(self, tmp_path):
        cfg = LogConfig(service="test")
        assert cfg.service == "test"
        assert cfg.env == "dev"
        assert cfg.level == LogLevel.INFO
        assert cfg.console is True
        assert cfg.file is True
        assert cfg.remote is False
        assert cfg.file_max_size == 10 * 1024 * 1024
        assert cfg.file_backup_count == 30
        assert cfg.queue_maxsize == 65536
        assert cfg.max_msg_bytes == 64 * 1024
        assert cfg.drop_policy == "oldest"
        assert cfg.redact_enabled is True

    def test_str_level_converted(self, tmp_path):
        cfg = LogConfig(service="t", level="DEBUG", log_dir=str(tmp_path))
        assert isinstance(cfg.level, LogLevel)
        assert cfg.level == LogLevel.DEBUG

    def test_creates_log_dir(self, tmp_path):
        log_dir = os.path.join(str(tmp_path), "subdir", "logs")
        cfg = LogConfig(service="t", file=True, log_dir=log_dir)
        assert os.path.exists(log_dir)

    def test_file_false_skip_dir_creation(self, tmp_path):
        # file=False 时不应主动创建目录
        log_dir = os.path.join(str(tmp_path), "no_create")
        cfg = LogConfig(service="t", file=False, log_dir=log_dir)
        assert not os.path.exists(log_dir)

    def test_extra_redact_keys_default_empty(self, tmp_path):
        cfg = LogConfig(service="t", log_dir=str(tmp_path))
        assert cfg.extra_redact_keys == []
