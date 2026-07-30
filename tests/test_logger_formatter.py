"""格式化模块测试"""

import json

import pytest

from mini_logger.config import LogLevel
from mini_logger.formatter import (
    now_iso_ms,
    build_record,
    format_json,
    format_human,
    format_record,
    supports_color,
)


class TestNowIsoMs:
    def test_returns_iso_string_with_offset(self):
        ts = now_iso_ms()
        # 形如 2026-07-31T14:30:00.123+08:00
        assert "+08:00" in ts
        assert "T" in ts
        # 毫秒部分：".123+08:00" 中的 "." 在 +08:00 前 4 位
        # 即倒数第 10 个字符是 "."
        assert ts[-10:-9] == "."

    def test_millisecond_precision(self):
        ts = now_iso_ms()
        # 毫秒为 3 位数字，紧跟在 "." 之后，"+" 之前
        # 形如 ...00.123+08:00，提取 "." 与 "+" 之间部分
        dot_idx = ts.rfind(".")
        plus_idx = ts.rfind("+")
        ms_part = ts[dot_idx + 1 : plus_idx]
        assert len(ms_part) == 3
        assert ms_part.isdigit()


class TestBuildRecord:
    def _make_record(self, **overrides):
        defaults = dict(
            level=LogLevel.INFO,
            service="test-svc",
            msg="hello",
            trace_id="trace-123",
            span_id="",
            request_id="",
            user_id="",
            client_ip="",
            tenant="",
            module="",
            func="",
            line=0,
            err_type="",
            err_stack="",
            extra={},
        )
        defaults.update(overrides)
        return build_record(**defaults)

    def test_required_fields_present(self):
        r = self._make_record()
        assert r["ts"]
        assert r["level"] == "INFO"
        assert r["service"] == "test-svc"
        assert r["trace_id"] == "trace-123"
        assert r["msg"] == "hello"

    def test_optional_fields_omitted_when_empty(self):
        r = self._make_record(span_id="", user_id="")
        assert "span_id" not in r
        assert "user_id" not in r
        assert "module" not in r
        assert "func" not in r

    def test_optional_fields_present_when_set(self):
        r = self._make_record(span_id="s1", user_id="u1", client_ip="1.1.1.1", line=42)
        assert r["span_id"] == "s1"
        assert r["user_id"] == "u1"
        assert r["client_ip"] == "1.1.1.1"
        assert r["line"] == 42

    def test_exception_fields(self):
        r = self._make_record(err_type="ValueError", err_stack="Traceback ...")
        assert r["err_type"] == "ValueError"
        assert r["err_stack"] == "Traceback ..."

    def test_extra_present(self):
        r = self._make_record(extra={"k": "v"})
        assert r["extra"] == {"k": "v"}


class TestFormatJson:
    def test_returns_valid_json(self):
        rec = {"ts": "2026-01-01T00:00:00.000+08:00", "level": "INFO", "msg": "x"}
        s = format_json(rec)
        parsed = json.loads(s)
        assert parsed["level"] == "INFO"
        assert parsed["msg"] == "x"

    def test_chinese_not_escaped(self):
        rec = {"msg": "中文消息"}
        s = format_json(rec)
        assert "中文消息" in s
        assert "\\u" not in s


class TestFormatHuman:
    def test_contains_key_info(self):
        rec = {
            "ts": "2026-01-01T00:00:00.000+08:00",
            "level": "INFO",
            "service": "svc",
            "trace_id": "abcd1234efgh5678",
            "msg": "hello world",
        }
        s = format_human(rec)
        assert "INFO" in s
        assert "svc" in s
        assert "abcd1234" in s  # trace_id 截断为 8 位
        assert "hello world" in s

    def test_includes_extra_fields(self):
        rec = {
            "ts": "2026-01-01T00:00:00.000+08:00",
            "level": "ERROR",
            "service": "svc",
            "trace_id": "abcd1234",
            "msg": "err",
            "err_type": "ValueError",
            "err_stack": "Traceback (most recent call last):\n  File ...",
            "extra": {"k": "v"},
        }
        s = format_human(rec)
        assert "err_type=ValueError" in s
        assert "Traceback" in s
        assert '"k": "v"' in s or "'k': 'v'" in s or "extra=" in s


class TestFormatRecord:
    def test_json_dispatch(self):
        rec = {"level": "INFO", "msg": "x"}
        s_json = format_record(rec, as_json=True)
        assert s_json.startswith("{")

    def test_human_dispatch(self):
        rec = {"level": "INFO", "msg": "x", "ts": "2026-01-01T00:00:00.000+08:00", "service": "s", "trace_id": "abcd1234"}
        s_human = format_record(rec, as_json=False)
        assert not s_human.startswith("{")


class TestSupportsColor:
    def test_returns_bool(self):
        assert isinstance(supports_color(), bool)
