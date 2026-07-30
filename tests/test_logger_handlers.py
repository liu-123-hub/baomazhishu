"""handlers 模块测试"""

import os
import time
import threading

import pytest

from mini_logger.config import LogConfig
from mini_logger.handlers import (
    BaseHandler,
    ConsoleHandler,
    RollingFileHandler,
    RemoteHandler,
)


class TestBaseHandler:
    def test_emit_not_implemented(self):
        h = BaseHandler()
        with pytest.raises(NotImplementedError):
            h.emit("x")

    def test_flush_and_close_default_noop(self):
        h = BaseHandler()
        h.flush()  # 不应抛异常
        h.close()


class TestConsoleHandler:
    def test_emit_writes_to_stdout(self, capsys):
        h = ConsoleHandler(as_json=False)
        h.emit("hello-stdout")
        captured = capsys.readouterr()
        assert "hello-stdout" in captured.out

    def test_emit_swallows_exception(self, monkeypatch):
        # 模拟 stdout.write 抛异常（如管道已关闭）
        h = ConsoleHandler()

        def raise_io(*a, **kw):
            raise IOError("broken pipe")

        import sys
        monkeypatch.setattr(sys.stdout, "write", raise_io)
        # 不应抛异常
        h.emit("x")


class TestRollingFileHandler:
    def _make_config(self, tmp_path, **overrides):
        defaults = dict(
            service="test",
            log_dir=str(tmp_path),
            file_max_size=1024,  # 1KB 便于测试
            file_backup_count=3,
        )
        defaults.update(overrides)
        return LogConfig(**defaults)

    def test_writes_to_file(self, tmp_path):
        cfg = self._make_config(tmp_path)
        h = RollingFileHandler(cfg)
        h.emit("line1")
        h.emit("line2")
        h.flush()
        h.close()

        files = os.listdir(cfg.log_dir)
        assert any(f.startswith("test-") and f.endswith(".log") for f in files)
        content = ""
        for f in files:
            with open(os.path.join(cfg.log_dir, f), "r", encoding="utf-8") as fp:
                content = fp.read()
        assert "line1" in content
        assert "line2" in content

    def test_size_rotation(self, tmp_path):
        cfg = self._make_config(tmp_path, file_max_size=50)
        h = RollingFileHandler(cfg)
        # 写入大量数据触发滚动
        for i in range(20):
            h.emit(f"line-{i:03d}-padding-xxxxxxxxxxxxxxxx")
        h.flush()
        h.close()
        files = os.listdir(cfg.log_dir)
        # 应该有 .1, .2 等滚动文件
        assert any(".log.1" in f for f in files)

    def test_cleanup_old_files(self, tmp_path):
        cfg = self._make_config(tmp_path, file_backup_count=2)
        # 预先创建一批过期文件
        for d in ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04", "2020-01-05"]:
            p = os.path.join(cfg.log_dir, f"test-{d}.log")
            with open(p, "w") as fp:
                fp.write("old")
            old_mtime = time.time() - 60 * 60 * 24 * 100  # 100 天前
            os.utime(p, (old_mtime, old_mtime))
        # 重新初始化 handler，应清理
        h = RollingFileHandler(cfg)
        h.close()
        files = [f for f in os.listdir(cfg.log_dir) if f.startswith("test-")]
        # backup_count=2，应该只剩 2 个 .log 文件（可能不含当天新建的）
        # 至少不应再有 5 个旧文件
        assert len(files) <= 3

    def test_close_releases_file(self, tmp_path):
        cfg = self._make_config(tmp_path)
        h = RollingFileHandler(cfg)
        h.close()
        assert h._fp is None

    def test_emit_after_close_no_crash(self, tmp_path):
        cfg = self._make_config(tmp_path)
        h = RollingFileHandler(cfg)
        h.close()
        h.emit("after-close")  # 不应抛异常


class TestRemoteHandler:
    def test_emit_buffers_until_batch(self):
        cfg = LogConfig(
            service="t",
            file=False,
            remote=True,
            remote_url="http://localhost:9999/never-reachable",
            remote_batch_size=3,
        )
        h = RemoteHandler(cfg)
        h.emit("r1")
        h.emit("r2")
        # 未达 batch_size，应缓存
        assert len(h.batch) == 2
        h.close()

    def test_emit_triggers_send_at_batch(self, monkeypatch):
        cfg = LogConfig(
            service="t",
            file=False,
            remote=True,
            remote_url="http://localhost:9999/never-reachable",
            remote_batch_size=2,
            remote_timeout=0.1,
        )
        h = RemoteHandler(cfg)

        sent_batches = []

        def fake_send(self_inner):
            sent_batches.append(list(self_inner.batch))
            self_inner.batch.clear()

        monkeypatch.setattr(RemoteHandler, "_send_batch", fake_send)
        h.emit("r1")
        h.emit("r2")  # 达 batch_size，触发 send
        assert len(sent_batches) == 1
        assert len(sent_batches[0]) == 2
        h.close()

    def test_send_batch_swallows_network_error(self):
        cfg = LogConfig(
            service="t",
            file=False,
            remote=True,
            remote_url="http://127.0.0.1:1/unreachable",
            remote_timeout=0.05,
            remote_batch_size=1,
        )
        h = RemoteHandler(cfg)
        h.emit("x")  # 立即触发 send，连接被拒
        # 不应抛异常，且 batch 被清空
        assert h.batch == []

    def test_flush_sends_pending(self, monkeypatch):
        cfg = LogConfig(
            service="t",
            file=False,
            remote=True,
            remote_url="http://localhost:9999/x",
            remote_batch_size=100,
        )
        h = RemoteHandler(cfg)
        sent = {"count": 0}

        def fake_send(self_inner):
            sent["count"] += len(self_inner.batch)
            self_inner.batch.clear()

        monkeypatch.setattr(RemoteHandler, "_send_batch", fake_send)
        h.emit("a")
        h.emit("b")
        h.flush()
        assert sent["count"] == 2
        h.close()

    def test_no_url_skips(self):
        cfg = LogConfig(service="t", file=False, remote=False, remote_url=None)
        # remote=False，不应实例化 RemoteHandler（在 Logger 层校验）
        # 此处直接测试 RemoteHandler 在 url=None 时的行为
        h = RemoteHandler(cfg)
        h.emit("x")
        # url 为空时 _send_batch 直接 return
        h.flush()
        h.close()
