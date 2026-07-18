"""数据真实性校验模块，生成 data provenance 用于 API 溯源。"""
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any


MAX_DATA_AGE_HOURS = 72
MAX_FUTURE_SKEW_MINUTES = 10
MIN_POSTS_PER_SECTOR = 1

REQUIRED_PROVENANCE_FIELDS = (
    # source_name 在 authenticate_collected_data 入参层面已校验，
    # 帖子级别只需保证采集时间与原始链接可追溯。
    "collected_at",
    ("source_url", "url"),  # 允许 source_url 或 url 作为溯源链接
)

LEGIT_SOURCE_NAMES = frozenset({
    "东方财富股吧",
    "小红书",
    "雪球社区",
    "Google News",
    "网易财经",
    "东方财富资讯",
    "同花顺财经",
    "行情数据(AKShare)",
    "市场异动数据(AKShare)",
})


class AuthenticityError(Exception):
    """数据真实性校验失败异常。"""


def _parse_iso_datetime(dt_str: str) -> Optional[datetime]:
    if not isinstance(dt_str, str) or not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except (ValueError, TypeError):
        return None


def verify_timestamp_freshness(collected_at: str, source_name: str) -> List[str]:
    issues: List[str] = []
    dt = _parse_iso_datetime(collected_at)
    if dt is None:
        issues.append(f"{source_name}: collected_at 不是合法 ISO 时间: {collected_at}")
        return issues

    now = datetime.now()
    if dt < now - timedelta(hours=MAX_DATA_AGE_HOURS):
        issues.append(
            f"{source_name}: 数据已过期，采集时间 {collected_at} 早于 {MAX_DATA_AGE_HOURS} 小时前"
        )
    if dt > now + timedelta(minutes=MAX_FUTURE_SKEW_MINUTES):
        issues.append(
            f"{source_name}: 时间戳超前当前时间 {MAX_FUTURE_SKEW_MINUTES} 分钟以上，疑似伪造"
        )
    return issues


def verify_source_legitimacy(source_name: str) -> List[str]:
    issues: List[str] = []
    if source_name not in LEGIT_SOURCE_NAMES:
        issues.append(
            f"数据源「{source_name}」不在合法白名单内，合规数据源列表: {sorted(LEGIT_SOURCE_NAMES)}"
        )
    return issues


def verify_data_completeness(
    sector_data: Dict[str, List[Dict]],
    source_name: str,
) -> List[str]:
    issues: List[str] = []
    if not isinstance(sector_data, dict):
        issues.append(f"{source_name}: 板块数据不是字典结构")
        return issues

    for sector, posts in sector_data.items():
        if not isinstance(posts, list):
            issues.append(f"{source_name}/{sector}: 板块数据不是列表")
            continue
        if len(posts) == 0:
            continue
        for i, post in enumerate(posts):
            if not isinstance(post, dict):
                issues.append(f"{source_name}/{sector}[{i}]: 帖子不是字典结构")
                continue
            for field in ("id", "title", "platform", "collected_at"):
                val = post.get(field)
                if val is None or (isinstance(val, str) and not val.strip()):
                    issues.append(f"{source_name}/{sector}/{post.get('id', f'#{i}')}: 缺少字段 {field}")
            for field_spec in REQUIRED_PROVENANCE_FIELDS:
                # field_spec 可以是单个字段名，也可以是多个候选字段名的元组
                candidate_fields = (field_spec,) if isinstance(field_spec, str) else field_spec
                if not any(f in post for f in candidate_fields):
                    display_field = candidate_fields[0]
                    if display_field == "collected_at":
                        continue
                    issues.append(
                        f"{source_name}/{sector}/{post.get('id', f'#{i}')}: "
                        f"缺少溯源字段 {display_field}（数据真实性要求）"
                    )
    return issues


def compute_data_fingerprint(payload: Any) -> str:
    try:
        if isinstance(payload, (dict, list)):
            serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        else:
            serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception as e:
        return f"fingerprint_error:{type(e).__name__}"


def authenticate_collected_data(
    source_name: str,
    sector_data: Dict[str, List[Dict]],
    collected_at: Optional[str] = None,
) -> Dict[str, Any]:
    """对一次采集结果执行完整真实性校验。

    判定规则：
    - passed=True 仅当无校验问题 **且** 采集到 >0 条记录。
      空结果可能是被风控/限流/网络异常导致，不应视为"通过"，
      否则会误导前端展示"6/6 源通过"而实际无用户讨论数据。
    - record_count=0 时标记 passed=False 并追加 issue。
    """
    if collected_at is None:
        collected_at = datetime.now().isoformat()

    issues: List[str] = []

    issues.extend(verify_source_legitimacy(source_name))
    issues.extend(verify_timestamp_freshness(collected_at, source_name))
    issues.extend(verify_data_completeness(sector_data, source_name))

    total_records = sum(
        len(posts) for posts in sector_data.values()
        if isinstance(posts, list)
    )

    # 关键修复：0 条记录不应视为校验通过。
    # 之前空结果也会 passed=True，导致 data_provenance 显示"6/6 源通过"
    # 但实际所有用户讨论源都为空，前端会误认为数据正常。
    if total_records == 0:
        issues.append(
            f"{source_name}: 采集记录数为 0，可能被风控/限流或网络异常，标记为未通过"
        )

    fingerprint = compute_data_fingerprint({
        "source_name": source_name,
        "collected_at": collected_at,
        "sector_data": sector_data,
    })

    return {
        "source_name": source_name,
        "passed": len(issues) == 0,
        "issues": issues,
        "fingerprint": fingerprint,
        "record_count": total_records,
        "collected_at": collected_at,
        "checked_at": datetime.now().isoformat(),
    }


def is_data_fresh(latest_update_time: Optional[str], max_age_hours: int = 24) -> Dict[str, Any]:
    if not latest_update_time:
        return {
            "is_fresh": False,
            "age_hours": None,
            "stale_reason": "无更新时间记录",
        }

    dt = _parse_iso_datetime(latest_update_time)
    if dt is None:
        return {
            "is_fresh": False,
            "age_hours": None,
            "stale_reason": f"无法解析时间: {latest_update_time}",
        }

    age = datetime.now() - dt
    age_hours = round(age.total_seconds() / 3600, 2)

    if age > timedelta(hours=max_age_hours):
        return {
            "is_fresh": False,
            "age_hours": age_hours,
            "stale_reason": f"数据已过期（{age_hours}小时，超过 {max_age_hours} 小时）",
        }

    return {
        "is_fresh": True,
        "age_hours": age_hours,
        "stale_reason": "",
    }


def build_data_provenance(
    auth_reports: List[Dict[str, Any]],
    total_records: int,
) -> Dict[str, Any]:
    passed = [r for r in auth_reports if r.get("passed")]
    passed_with_data = [r for r in passed if r.get("record_count", 0) > 0]

    # 用户讨论型数据源（用于判定"是否有人气数据"而非纯新闻流）
    USER_DISCUSSION_SOURCES = frozenset({
        "东方财富股吧", "小红书", "雪球社区",
    })
    user_discussion_reports = [
        r for r in auth_reports if r.get("source_name") in USER_DISCUSSION_SOURCES
    ]
    user_discussion_passed = [
        r for r in user_discussion_reports if r.get("passed") and r.get("record_count", 0) > 0
    ]

    # has_user_discussion: 是否有任一用户讨论源采集到 >0 条记录。
    # 若为 False，说明仅采集到新闻/资讯，指数计算会因缺少小白语境失真，
    # 前端应明确提示"缺少用户讨论数据"而非"真实数据"。
    has_user_discussion = len(user_discussion_passed) > 0

    return {
        "is_real_data": len(passed_with_data) > 0,
        "has_user_discussion": has_user_discussion,
        "user_discussion_count": len(user_discussion_passed),
        "user_discussion_total": len(user_discussion_reports),
        "source_count": len(auth_reports),
        "passed_count": len(passed),
        "passed_with_data_count": len(passed_with_data),
        "total_records": total_records,
        "fingerprints": [
            {
                "source_name": r["source_name"],
                "fingerprint": r["fingerprint"],
                "record_count": r["record_count"],
                "passed": r["passed"],
                # 持久化 issues 字段，便于前端展示与后续诊断。
                # 失败原因不再仅打印到控制台后丢弃。
                "issues": r.get("issues", []),
                "collected_at": r.get("collected_at"),
                "checked_at": r.get("checked_at"),
            }
            for r in auth_reports
        ],
        "generated_at": datetime.now().isoformat(),
    }
