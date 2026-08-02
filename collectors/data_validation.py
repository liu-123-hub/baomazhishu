"""数据校验工具，采集数据进入分析链路前的字段、时效和去重校验。"""
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

REQUIRED_POST_FIELDS = ("id", "title", "platform", "collected_at")
MAX_SOURCE_AGE_HOURS = 72
MAX_FUTURE_SKEW_MINUTES = 10
MAX_TITLE_LENGTH = 160

_HTML_TAG_PATTERN = re.compile(r"<\s*(script|iframe|img|style|link|meta|form|input|button|svg|on\w+)", re.IGNORECASE)


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_post(post: Dict, source_name: str, sector: str) -> List[str]:
    errors: List[str] = []

    if not isinstance(post, dict):
        return [f"{source_name}/{sector}: 帖子不是字典结构"]

    for field in REQUIRED_POST_FIELDS:
        if not _is_non_empty_string(post.get(field)):
            errors.append(f"{source_name}/{sector}/{post.get('id', 'unknown')}: 缺少字段 {field}")

    collected_at = post.get("collected_at")
    if _is_non_empty_string(collected_at):
        try:
            collected_dt = datetime.fromisoformat(collected_at)
            if collected_dt.tzinfo is not None:
                collected_dt = collected_dt.replace(tzinfo=None)
            now = datetime.now()
            if collected_dt < now - timedelta(hours=MAX_SOURCE_AGE_HOURS):
                errors.append(
                    f"{source_name}/{sector}/{post.get('id', 'unknown')}: 数据已过期({collected_at})"
                )
            if collected_dt > now + timedelta(minutes=MAX_FUTURE_SKEW_MINUTES):
                errors.append(
                    f"{source_name}/{sector}/{post.get('id', 'unknown')}: 时间戳超前({collected_at})"
                )
        except ValueError:
            errors.append(
                f"{source_name}/{sector}/{post.get('id', 'unknown')}: collected_at 不是合法 ISO 时间"
            )

    title = post.get("title", "")
    if isinstance(title, str) and len(title.strip()) > MAX_TITLE_LENGTH:
        errors.append(
            f"{source_name}/{sector}/{post.get('id', 'unknown')}: 标题长度超过 {MAX_TITLE_LENGTH} 字符"
        )

    if isinstance(title, str) and _HTML_TAG_PATTERN.search(title):
        errors.append(
            f"{source_name}/{sector}/{post.get('id', 'unknown')}: 标题包含潜在 HTML 注入标签"
        )

    content = post.get("content", "")
    if content is not None and not isinstance(content, str):
        errors.append(
            f"{source_name}/{sector}/{post.get('id', 'unknown')}: content 需为字符串"
        )

    url = post.get("url", "")
    if url and isinstance(url, str):
        if "javascript:" in url.lower():
            errors.append(
                f"{source_name}/{sector}/{post.get('id', 'unknown')}: url 包含 javascript 协议"
            )
        elif not url.startswith(("http://", "https://")):
            errors.append(
                f"{source_name}/{sector}/{post.get('id', 'unknown')}: url 非 http/https 协议"
            )

    return errors


def validate_dashboard_for_sync(dashboard: Dict) -> Tuple[bool, List[str]]:
    issues: List[str] = []

    if not isinstance(dashboard, dict):
        return (False, ["dashboard 数据不是字典结构，拒绝同步"])

    for key in ("latest", "record_count", "data_provenance"):
        if key not in dashboard:
            issues.append(f"dashboard 缺少顶层字段: {key}")

    if issues:
        return (False, issues)

    latest = dashboard.get("latest")
    if not isinstance(latest, dict):
        return (False, ["dashboard.latest 不是字典结构"])

    record_date = latest.get("date")
    if not record_date or not isinstance(record_date, str):
        issues.append("dashboard.latest.date 缺失或非字符串，无法判定数据日期")

    sectors = latest.get("sectors")
    if not isinstance(sectors, dict) or len(sectors) == 0:
        issues.append("dashboard.latest.sectors 缺失或为空，无有效板块数据")
        return (False, issues)

    valid_sector_count = 0
    for code, data in sectors.items():
        if not isinstance(data, dict):
            issues.append(f"板块 [{code}] 数据不是字典结构，跳过")
            continue
        details = data.get("details") or {}
        total_posts = details.get("total_posts", 0)
        index_value = data.get("index")
        buy_idx = details.get("mom_buy_index")
        sell_idx = details.get("mom_sell_index")

        if not isinstance(total_posts, int) or total_posts <= 0:
            continue
        if not isinstance(index_value, (int, float)):
            issues.append(f"板块 [{code}] index 非数值: {index_value}")
            continue
        if not isinstance(buy_idx, (int, float)) or not isinstance(sell_idx, (int, float)):
            issues.append(f"板块 [{code}] buy/sell 指数非数值")
            continue
        valid_sector_count += 1

    if valid_sector_count == 0:
        issues.append("所有板块均未通过完整性校验（total_posts>0 且 index/buy/sell 为数值），拒绝同步")

    provenance = dashboard.get("data_provenance") or {}
    if not isinstance(provenance, dict):
        issues.append("dashboard.data_provenance 不是字典结构")
    else:
        has_user_discussion = provenance.get("has_user_discussion")
        if has_user_discussion is False:
            issues.append("数据降级：所有用户讨论源均无记录(has_user_discussion=False)，拒绝覆盖本地数据")

    return (len(issues) == 0, issues)


def validate_source_posts(
    source_name: str, source_posts: Dict[str, List[Dict]]
) -> Tuple[Dict[str, List[Dict]], List[str]]:
    cleaned: Dict[str, List[Dict]] = {}
    issues: List[str] = []

    for sector, posts in source_posts.items():
        if not isinstance(posts, list):
            issues.append(f"{source_name}/{sector}: 板块数据不是列表，已跳过")
            cleaned[sector] = []
            continue

        seen_ids = set()
        valid_posts: List[Dict] = []

        for post in posts:
            errors = validate_post(post, source_name, sector)
            if errors:
                issues.extend(errors)
                continue

            post_id = post.get("id") if isinstance(post, dict) else None

            if post_id in seen_ids:
                issues.append(f"{source_name}/{sector}/{post_id}: 重复帖子已去重")
                continue

            seen_ids.add(post_id)
            valid_posts.append(post)

        cleaned[sector] = valid_posts

    return cleaned, issues
