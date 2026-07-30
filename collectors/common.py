"""采集器公共工具：HTML 清洗、HTTP 重试、板块归类等共享逻辑。

板块分类 v2.0：支持双重归属——每条帖子可同时归入最多3个板块
（1个主匹配板块 + 最多2个关联板块），实现标准行业 + 跨行业概念的多标签归类。
"""
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

# 双重归属的最大板块数（主板块 + 关联板块）
MAX_DUAL_SECTORS = 3
# 标题匹配权重（标题命中优先级远高于正文）
TITLE_MATCH_WEIGHT = 3
# 概念板块关键词长度阈值（更长的关键词=更具体=更高优先级）
CONCEPT_KEYWORD_PRIORITY_BONUS = 1


def clean_html(raw_html: str) -> str:
    """清除 HTML 标签并反转义实体，返回纯文本。"""
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
    """获取页面 HTML 文本，带重试与编码自适应。

    编码策略：优先使用响应头声明的 charset；若服务器未声明或 requests 回退
    到 ISO-8859-1，则用 apparent_encoding 自动检测（兼容 UTF-8/GBK）。
    """
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
    """按正则从 HTML 中提取新闻标题与链接，过滤导航类噪声。"""
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
    """计算板块匹配分数，返回 (score, matched_keyword_length, matched_keyword)。

    评分规则：
    - 标题命中：score += TITLE_MATCH_WEIGHT * 关键词长度（更具体的关键词分更高）
    - 正文命中：score += 关键词长度
    - 更长的关键词=更具体=优先级更高（避免"银行"匹配到"投资银行"等歧义时优先选更具体的）
    """
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
    """根据标题/描述关键词匹配，返回最佳匹配板块（单板块，向后兼容）。

    注意：v2.0推荐使用 classify_sectors() 获取多标签结果（支持双重归属）。
    本函数保留以兼容旧代码，返回得分最高的单一板块。
    """
    sectors = classify_sectors(title, description, sector_keywords, max_sectors=1)
    return sectors[0] if sectors else None


def classify_sectors(
    title: str,
    description: str,
    sector_keywords: Dict[str, List[str]],
    max_sectors: int = MAX_DUAL_SECTORS,
) -> List[str]:
    """多标签板块分类（v2.0 双重归属核心）：返回最多 max_sectors 个匹配板块。

    匹配逻辑：
    1. 对每个板块计算匹配分数（标题命中权重×关键词长度）
    2. 按分数降序排列，取前 max_sectors 个得分>0的板块
    3. 如果主板块是概念赛道(concept)，自动追加其关联的标准行业板块
    4. 去重后保证不超过 max_sectors 个

    返回: 匹配到的板块代码列表（按优先级排序，第一个为主板块）
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

    # 按分数降序排列
    sorted_sectors = sorted(scores.keys(), key=lambda s: scores[s], reverse=True)
    result = list(sorted_sectors)

    # 如果主板块是概念赛道，自动追加其关联行业板块（实现自动双重归属）
    if result and get_sector_type(result[0]) == "concept":
        related = get_related_sectors(result[0])
        for r in related:
            if r not in result and len(result) < max_sectors:
                result.append(r)

    # 去重并截断
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
    """将新闻 item 转为项目统一的 post 字典格式。"""
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
    """双重归属：为同一条新闻/帖子生成多个板块的 post 字典。

    返回: {sector_code: post_dict} 的字典，每个匹配板块一个 post。
    注意：每个 post 的 id 使用 sector 作为区分，保证同一帖子在不同板块中有不同 id。
    """
    result = {}
    for sector in sectors:
        result[sector] = make_post(item, sector, platform, id_prefix, author_default)
    return result


def empty_sector_result(sector_keywords: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
    """生成包含所有板块的空结果字典。"""
    return {sector: [] for sector in sector_keywords}
