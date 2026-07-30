"""mini_logger 格式化模块

提供两种输出格式：
- JSON 格式：便于 ELK / Loki 等日志平台解析
- 人类可读格式：终端调试友好，颜色高亮
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from typing import Any, Dict

from .config import LogLevel

# UTC+8 时区
_TZ_CN = timezone(timedelta(hours=8))

# ANSI 颜色码（控制台人类可读模式使用）
_COLOR = {
    LogLevel.DEBUG: "\033[36m",  # cyan
    LogLevel.INFO: "\033[32m",  # green
    LogLevel.WARN: "\033[33m",  # yellow
    LogLevel.ERROR: "\033[31m",  # red
    LogLevel.FATAL: "\033[35m",  # magenta
}
_RESET = "\033[0m"


def now_iso_ms() -> str:
    """当前 UTC+8 时间，ISO8601 含毫秒。例如 2026-07-31T14:30:00.123+08:00"""
    return datetime.now(_TZ_CN).isoformat(timespec="milliseconds")


def build_record(
    *,
    level: LogLevel,
    service: str,
    msg: str,
    trace_id: str,
    span_id: str,
    request_id: str,
    user_id: str,
    client_ip: str,
    tenant: str,
    module: str,
    func: str,
    line: int,
    err_type: str,
    err_stack: str,
    extra: Dict[str, Any],
) -> Dict[str, Any]:
    """构造完整日志字段 dict（未脱敏、未格式化）。"""
    rec: Dict[str, Any] = {
        "ts": now_iso_ms(),
        "level": level.name,
        "service": service,
        "trace_id": trace_id,
        "msg": msg,
    }
    # 仅在非空时写入可选字段，避免输出膨胀
    if span_id:
        rec["span_id"] = span_id
    if request_id:
        rec["request_id"] = request_id
    if user_id:
        rec["user_id"] = user_id
    if client_ip:
        rec["client_ip"] = client_ip
    if tenant:
        rec["tenant"] = tenant
    if module:
        rec["module"] = module
    if func:
        rec["func"] = func
    if line:
        rec["line"] = line
    if err_type:
        rec["err_type"] = err_type
    if err_stack:
        rec["err_stack"] = err_stack
    if extra:
        rec["extra"] = extra
    return rec


def format_json(record: Dict[str, Any]) -> str:
    """JSON 单行格式（ensure_ascii=False，便于中文直接阅读）。"""
    return json.dumps(record, ensure_ascii=False, default=str)


def format_human(record: Dict[str, Any]) -> str:
    """人类可读格式：颜色 + 紧凑字段。"""
    lvl = record.get("level", "INFO")
    try:
        level_enum = LogLevel[lvl]
    except KeyError:
        level_enum = LogLevel.INFO
    color = _COLOR.get(level_enum, "")
    ts = record.get("ts", "")
    svc = record.get("service", "")
    tid = record.get("trace_id", "-")[:8]
    msg = record.get("msg", "")

    head = f"{color}[{ts}] [{lvl:<5}] [{svc}] [trace={tid}]{_RESET} {msg}"

    parts: list[str] = [head]
    for k in ("user_id", "client_ip", "module", "func", "line", "request_id", "span_id"):
        if k in record and record[k]:
            parts.append(f"  {k}={record[k]}")
    if "err_type" in record:
        parts.append(f"  err_type={record['err_type']}")
    if "err_stack" in record:
        parts.append(f"  err_stack=\n{record['err_stack']}")
    if "extra" in record:
        parts.append(f"  extra={json.dumps(record['extra'], ensure_ascii=False, default=str)}")
    return "\n".join(parts)


def format_record(record: Dict[str, Any], as_json: bool) -> str:
    """根据 as_json 选择 JSON / 人类可读格式。"""
    return format_json(record) if as_json else format_human(record)


def supports_color() -> bool:
    """检测当前 stdout 是否支持 ANSI 颜色。"""
    return sys.stdout.isatty() and sys.platform != "win32"
