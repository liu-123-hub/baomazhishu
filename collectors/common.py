"""采集器公共工具：HTML 清洗、HTTP 重试、板块归类等共享逻辑。"""
import hashlib
import html
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests

DEFAULT_HTML_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}


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


def classify_sector(
    title: str,
    description: str,
    sector_keywords: Dict[str, List[str]],
) -> Optional[str]:
    """根据标题/描述关键词匹配，将新闻归入对应板块。先匹配标题，再匹配组合文本。"""
    combined = f"{title} {description}"

    for sector, keywords in sector_keywords.items():
        for kw in keywords:
            if kw in title:
                return sector
        for kw in keywords:
            if kw in combined:
                return sector

    return None


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
        "title": title[:100],
        "content": item.get("description", "")[:300],
        "url": link,
        "platform": platform,
        "author": item.get("source", author_default),
        "date": item.get("pub_date", ""),
        "collected_at": datetime.now().isoformat(),
    }


def empty_sector_result(sector_keywords: Dict[str, List[str]]) -> Dict[str, List[Dict]]:
    """生成包含所有板块的空结果字典。"""
    return {sector: [] for sector in sector_keywords}
