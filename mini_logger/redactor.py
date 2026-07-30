"""mini_logger 脱敏模块

内置规则：
- 身份证号（18 位）
- 手机号（11 位）
- 银行卡号（16-19 位）
- API Key / Token（长度 >= 16 的 token/key 字符串）
- 自定义敏感字段名（password / secret / token / key / pwd / passwd）

策略：
1. 字段名匹配：dict 中 key 命中敏感字段名 → 值替换为 "***"
2. 字符串扫描：在 msg 字符串中识别上述号码模式 → 局部遮蔽
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Set

# 默认敏感字段名（小写匹配）
_DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
    "apikey",
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "credit_card",
    "card_no",
    "id_card",
    "ssn",
}

# 正则：手机号（1 开头 11 位）
_PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
# 正则：身份证号（18 位，最后位可为 X）
_IDCARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
# 正则：银行卡号（16-19 位连续数字，且非手机/身份证）
_BANKCARD_RE = re.compile(r"(?<!\d)(\d{16,19})(?!\d)")
# 正则：长 token（连续字母数字下划线，长度 >= 20，包含 token 关键字的环境不在此处）
_LONG_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-Za-z0-9_-]{20,})(?![A-Za-z0-9])")


def _mask_middle(s: str, keep_head: int = 4, keep_tail: int = 4, mask: str = "*") -> str:
    """保留首尾若干位，中间用 * 填充。长度不足时全部遮蔽。"""
    n = len(s)
    if n <= keep_head + keep_tail:
        return mask * n
    return s[:keep_head] + mask * (n - keep_head - keep_tail) + s[-keep_tail:]


def redact_string(text: str) -> str:
    """对字符串中的敏感号码做局部遮蔽。"""
    if not text:
        return text

    # 优先级：身份证 > 手机 > 银行卡（避免误匹配）
    text = _IDCARD_RE.sub(lambda m: _mask_middle(m.group(1), 6, 4, "★"), text)
    text = _PHONE_RE.sub(lambda m: m.group(1)[:3] + "****" + m.group(1)[-4:], text)
    text = _BANKCARD_RE.sub(lambda m: _mask_middle(m.group(1), 4, 4), text)
    return text


def redact_dict(
    data: Dict[str, Any],
    extra_keys: Iterable[str] = (),
    visited: Optional[Set[int]] = None,
) -> Dict[str, Any]:
    """递归脱敏 dict。

    - 命中敏感字段名：值替换为 "***"
    - 普通字符串值：调用 redact_string 扫描号码
    - 嵌套 dict / list：递归处理
    """
    if visited is None:
        visited = set()
    obj_id = id(data)
    if obj_id in visited:  # 防止循环引用
        return data
    visited.add(obj_id)

    sensitive = _DEFAULT_SENSITIVE_KEYS | {k.lower() for k in extra_keys}
    out: Dict[str, Any] = {}
    for k, v in data.items():
        if isinstance(k, str) and k.lower() in sensitive:
            out[k] = "***"
        elif isinstance(v, dict):
            out[k] = redact_dict(v, extra_keys, visited)
        elif isinstance(v, list):
            out[k] = [
                redact_dict(item, extra_keys, visited)
                if isinstance(item, dict)
                else redact_string(item) if isinstance(item, str) else item
                for item in v
            ]
        elif isinstance(v, str):
            out[k] = redact_string(v)
        else:
            out[k] = v
    return out


def redact_any(value: Any, extra_keys: Iterable[str] = ()) -> Any:
    """统一入口：dict 走 redact_dict，str 走 redact_string，其他原样返回。"""
    if isinstance(value, dict):
        return redact_dict(value, extra_keys)
    if isinstance(value, str):
        return redact_string(value)
    return value
