import hashlib
import html
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests

DEFAULT_HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

MAX_DUAL_SECTORS = 3
TITLE_MATCH_WEIGHT = 3
CONCEPT_KEYWORD_PRIORITY_BONUS = 1


def clean_html(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_html_page(
    url: str,
    timeout: int = 15,
    max_retries: int = 3,
    retry_delay_base: int = 2,
    log_prefix: str = "",
    headers: Optional[Dict] = None,
) -> Optional[str]:
    """编码策略：优先使用响应头charset；若未声明或回退到ISO-8859-1，则用apparent_encoding检测（兼容UTF-8/GBK）。"""
    req_headers = headers or DEFAULT_HTML_HEADERS
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=req_headers, timeout=timeout)
            resp.raise_for_status()
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            return resp.text

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(retry_delay_base * (attempt + 1))
            else:
                print(f"    {log_prefix} 请求超时（已重试{max_retries}次）: {url}")

        except requests.exceptions.ConnectionError as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay_base * (attempt + 1))
            else:
                print(f"    {log_prefix} 连接失败（已重试{max_retries}次）: {e}")

        except requests.exceptions.HTTPError:
            status = resp.status_code if hasattr(resp, "status_code") else "N/A"
            if isinstance(status, int) and 400 <= status < 500:
                print(f"    {log_prefix} HTTP {status} 客户端错误，跳过: {url}")
                break
            if attempt < max_retries - 1:
                time.sleep(retry_delay_base * (attempt + 1))
            else:
                print(f"    {log_prefix} HTTP {status} 服务端错误，已重试 {max_retries} 次仍失败: {url}")

    return None


def parse_html_links(
    html_text: str,
    link_pattern: "re.Pattern",
    skip_keywords: List[str],
    source_name: str,
) -> List[Dict]:
    items: List[Dict] = []
    seen_links: set = set()

    for match in link_pattern.finditer(html_text):
        link = match.group(1).strip()
        title = clean_html(match.group(2))

        if not title or len(title) < 8:
            continue
        if any(sk in title for sk in skip_keywords):
            continue

        if link in seen_links:
            continue
        seen_links.add(link)

        items.append({
            "title": title,
            "link": link,
            "description": "",
            "source": source_name,
            "pub_date": "",
        })

    return items


def _compute_match_score(
    title: str,
    combined: str,
    keywords: List[str],
) -> Tuple[int, int, str]:
    """评分规则：标题命中权重×关键词长度，更长关键词=更具体=优先级更高。"""
    score = 0
    best_kw = ""
    best_kw_len = 0

    for kw in keywords:
        kw_len = len(kw)
        if kw in title:
            s = TITLE_MATCH_WEIGHT * kw_len
            if s > score or (s == score and kw_len > best_kw_len):
                score = s
                best_kw = kw
                best_kw_len = kw_len
        elif kw in combined and score == 0:
            s = kw_len
            if s > score or (s == score and kw_len > best_kw_len):
                score = s
                best_kw = kw
                best_kw_len = kw_len

    return score, best_kw_len, best_kw


def classify_sector(
    title: str,
    description: str,
    sector_keywords: Dict[str, List[str]],
) -> Optional[str]:
    sectors = classify_sectors(title, description, sector_keywords, max_sectors=1)
    return sectors[0] if sectors else None


def classify_sectors(
    title: str,
    description: str,
    sector_keywords: Dict[str, List[str]],
    max_sectors: int = MAX_DUAL_SECTORS,
) -> List[str]:
    """匹配逻辑：
    1. 每板块计算匹配分数（标题命中权重×关键词长度）
    2. 按分数降序取前max_sectors个得分>0的板块
    3. 主板块是概念赛道时自动追加关联行业板块
    4. 去重后不超过max_sectors个
    """
    from analyzer.index_calculator import get_sector_type, get_related_sectors

    combined = f"{title} {description}"
    scores: Dict[str, int] = {}

    for sector, keywords in sector_keywords.items():
        score, _, _ = _compute_match_score(title, combined, keywords)
        if score > 0:
            scores[sector] = score

    if not scores:
        return []

    sorted_sectors = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
    result = list(sorted_sectors)

    if result and get_sector_type(result[0]) == "concept":
        related = get_related_sectors(result[0])
        for r in related:
            if r not in result and len(result) < max_sectors:
                result.append(r)

    seen = set()
    unique_result = []
    for s in result:
        if s not in seen:
            seen.add(s)
            unique_result.append(s)

    return unique_result[:max_sectors]


def make_post(
    item: Dict,
    sector: str,
    platform: str,
    id_prefix: str,
    author_default: str,
) -> Dict:
    link = item["link"]
    title = item["title"]
    digest = hashlib.md5(link.encode("utf-8")).hexdigest()[:12]

    return {
        "id": f"{id_prefix}_{sector}_{digest}",
        "post_id": f"{id_prefix}_{sector}_{digest}",
        "sector": sector,
        "title": title[:100],
        "content": item.get("description", "")[:300],
        "url": link,
        "platform": platform,
        "author": item.get("source", author_default),
        "date": item.get("pub_date", ""),
        "collected_at": datetime.now().isoformat(),
    }


def make_multi_sector_posts(
    item: Dict,
    sectors: List[str],
    platform: str,
    id_prefix: str,
    author_default: str,
) -> Dict[str, Dict]:
    result = {}
    for sector in sectors:
        result[sector] = make_post(item, sector, platform, id_prefix, author_default)
    return result


def empty_sector_result(sector_keywords: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
    return {sector: [] for sector in sector_keywords}
