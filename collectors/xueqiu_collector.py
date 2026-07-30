"""东方财富资讯采集器，HTML 解析公开新闻并按板块分类。"""
import os
import sys
from typing import Dict, List
from urllib.parse import urlparse
import re
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analyzer.sector_keywords import get_all_sector_keywords
from collectors.common import (
    classify_sectors,
    empty_sector_result,
    fetch_html_page,
    make_multi_sector_posts,
    parse_html_links,
)

SECTOR_KEYWORDS: Dict[str, List[str]] = get_all_sector_keywords()
ALL_SECTORS: List[str] = list(SECTOR_KEYWORDS.keys())

NEWS_PAGES = [
    "https://finance.eastmoney.com/a/cgsxw.html",
]

REQUEST_TIMEOUT = 15
MAX_ITEMS_PER_PAGE = 60
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2

SKIP_KEYWORDS = ["首页", "登录", "注册", "下载", "更多", "返回", "网站地图",
                 "查看", "关于", "联系", "下一页", "上一页"]

_LINK_PATTERN = re.compile(
    r'<a[^>]*href="(https?://[^"]*eastmoney\.com/a/\d+\.html)"[^>]*>([^<]{8,120})</a>',
    re.IGNORECASE,
)


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有资讯页面，按板块关键词分类后返回。"""
    result = empty_sector_result(SECTOR_KEYWORDS)
    seen_links: set = set()

    for page_url in NEWS_PAGES:
        html_text = fetch_html_page(
            page_url, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY_BASE, "[东方财富资讯]"
        )
        if html_text is None:
            continue

        items = parse_html_links(html_text, _LINK_PATTERN, SKIP_KEYWORDS, "东方财富资讯")[:MAX_ITEMS_PER_PAGE]

        matched_count = 0
        for item in items:
            link = item.get("link", "")
            if link in seen_links:
                continue

            sectors = classify_sectors(item["title"], item.get("description", ""), SECTOR_KEYWORDS)
            if not sectors:
                continue

            seen_links.add(link)
            posts_by_sector = make_multi_sector_posts(item, sectors, "eastmoney_news", "em", "东方财富资讯")
            for sector, post in posts_by_sector.items():
                result[sector].append(post)
            matched_count += 1

        print(f"  [东方财富资讯] {urlparse(page_url).path} 共 {len(items)} 条，命中板块 {matched_count} 条")
        time.sleep(1)

    for sector, posts in result.items():
        if posts:
            print(f"  [东方财富资讯-{sector}] 采集到 {len(posts)} 条")

    return result


if __name__ == "__main__":  # pragma: no cover
    data = collect_all()
    for key, value in data.items():
        print(f"{key}: {len(value)} posts")
