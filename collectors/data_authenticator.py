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
    "collected_at",
    ("source_url", "url"),
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
    duration_ms: Optional[float] = None,
    http_latency_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """对采集结果执行真实性校验，0条记录不视为通过。"""
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
        "duration_ms": round(duration_ms, 1) if duration_ms is not None else None,
        "http_latency_ms": round(http_latency_ms, 1) if http_latency_ms is not None else None,
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
    source_durations: Optional[Dict[str, float]] = None,
    health_check_latencies: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    passed = [r for r in auth_reports if r.get("passed")]
    passed_with_data = [r for r in passed if r.get("record_count", 0) > 0]

    USER_DISCUSSION_SOURCES = frozenset({
        "东方财富股吧", "小红书", "雪球社区",
    })
    user_discussion_reports = [
        r for r in auth_reports if r.get("source_name") in USER_DISCUSSION_SOURCES
    ]
    user_discussion_passed = [
        r for r in user_discussion_reports if r.get("passed") and r.get("record_count", 0) > 0
    ]

    has_user_discussion = len(user_discussion_passed) > 0

    durations = [r.get("duration_ms") for r in auth_reports if r.get("duration_ms") is not None]
    latencies = [r.get("http_latency_ms") for r in auth_reports if r.get("http_latency_ms") is not None]
    
    performance_stats = {}
    if durations:
        performance_stats["total_collection_duration_ms"] = round(sum(durations), 1)
        performance_stats["avg_source_duration_ms"] = round(sum(durations) / len(durations), 1)
        performance_stats["max_source_duration_ms"] = round(max(durations), 1)
        performance_stats["min_source_duration_ms"] = round(min(durations), 1)
    if latencies:
        performance_stats["avg_http_latency_ms"] = round(sum(latencies) / len(latencies), 1)
        performance_stats["max_http_latency_ms"] = round(max(latencies), 1)

    return {
        "is_real_data": len(passed_with_data) > 0,
        "has_user_discussion": has_user_discussion,
        "user_discussion_count": len(user_discussion_passed),
        "user_discussion_total": len(user_discussion_reports),
        "source_count": len(auth_reports),
        "passed_count": len(passed),
        "passed_with_data_count": len(passed_with_data),
        "total_records": total_records,
        "performance_stats": performance_stats,
        "fingerprints": [
            {
                "source_name": r["source_name"],
                "fingerprint": r["fingerprint"],
                "record_count": r["record_count"],
                "passed": r["passed"],
                "issues": r.get("issues", []),
                "collected_at": r.get("collected_at"),
                "checked_at": r.get("checked_at"),
                "duration_ms": r.get("duration_ms"),
                "http_latency_ms": r.get("http_latency_ms"),
            }
            for r in auth_reports
        ],
        "generated_at": datetime.now().isoformat(),
    }
