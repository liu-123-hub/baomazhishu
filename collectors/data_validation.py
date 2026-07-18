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


def validate_source_posts(
    source_name: str, source_posts: Dict[str, List[Dict]]
) -> Tuple[Dict[str, List[Dict]], List[str]]:
    """校验单个数据源的板块数据，返回清洗后的结果。

    先校验有效性再去重，确保无效帖的错误能被正确报告。
    """
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
