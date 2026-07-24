"""Google News RSS 采集器，无需 API Key，为各板块补充公开新闻信号。"""
import hashlib
import html
import re
import time
from datetime import datetime
from typing import Dict, List
from urllib.parse import quote_plus
from xml.etree import ElementTree as ET

import requests

RSS_TEMPLATE = (
    "https://news.google.com/rss/search?q={query}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
)

# 采集参数集中管理，便于调优
MAX_RETRIES = 2                # 单关键词最大重试次数（不含首次）
RETRY_BACKOFF_BASE = 1.5       # 指数退避基数（秒）
REQUEST_INTERVAL = 0.4         # 相邻请求最小间隔，避免触发 IP 级限流
_CONNECT_TIMEOUT = 5           # 连接超时
_READ_TIMEOUT = 15             # 读取超时

# 浏览器风格的 User-Agent，避免被 Google News 识别为爬虫降级响应
_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

# 模块级 Session：复用 TCP/TLS 连接，避免 75 次请求各开新连接
_session: requests.Session = requests.Session()
_session.headers.update({"User-Agent": _BROWSER_UA})
_last_request_ts = 0.0

SEARCH_KEYWORDS = {
    "nasdaq": ["纳指100 ETF", "纳斯达克 ETF", "美股 ETF 纳指"],
    "gold": ["黄金 ETF", "黄金 基金 ETF", "黄金 投资 ETF"],
    "cpo": ["CPO ETF", "通信 ETF 光模块", "5G 通信 ETF"],
    "semiconductor": ["半导体 ETF", "芯片 ETF", "科创芯片 ETF"],
    "bank": ["银行 ETF", "银行股 基金", "金融 ETF 银行"],
    "securities": ["证券 ETF", "券商 ETF", "证券公司 ETF"],
    "biotech": ["创新药 ETF", "医药 ETF", "生物医药 ETF"],
    "consumer": ["消费 ETF", "食品饮料 ETF", "白酒 ETF"],
    "newenergy": ["新能源 ETF", "光伏 ETF", "新能源车 ETF"],
    "insurance": ["保险 ETF", "保险 股票", "金融 保险"],
    "baijiu": ["白酒 ETF", "酒 ETF 基金", "白酒 股票"],
    "food": ["食品 ETF", "食品饮料 ETF", "调味品 股票"],
    "medicine": ["医药 ETF", "医疗 ETF", "医疗器械 股票"],
    "appliance": ["家电 ETF", "家电 股票", "白色家电 基金"],
    "tourism": ["旅游 ETF", "文旅 ETF", "免税 股票"],
    "electronics": ["电子 ETF", "消费电子 ETF", "电子 股票"],
    "computer": ["计算机 ETF", "软件 ETF", "信创 股票"],
    "communication": ["5G 通信 ETF", "通信 ETF", "通信 股票"],
    "media": ["传媒 ETF", "游戏 ETF", "传媒 股票"],
    "nonferrous": ["有色 ETF", "有色金属 ETF", "有色金属 股票"],
    "coal": ["煤炭 ETF", "煤炭 股票", "动力煤 基金"],
    "chemical": ["化工 ETF", "化工 股票", "新材料 ETF"],
    "steel": ["钢铁 ETF", "钢铁 股票", "钢材 基金"],
    "realestate": ["房地产 ETF", "地产 ETF", "房地产 股票"],
    "infrastructure": ["基建 ETF", "建筑 ETF", "基建 股票"],
}


def _clean_html(raw_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rss(xml_text: str) -> List[Dict]:
    root = ET.fromstring(xml_text)
    items: List[Dict] = []

    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub_date = (item.findtext("pubDate") or "").strip()
        description = _clean_html(item.findtext("description") or "")
        source = (item.findtext("source") or "Google News").strip()

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "description": description,
                "source": source,
                "pub_date": pub_date,
            }
        )

    return items


def search_news(keyword: str, limit: int = 8) -> List[Dict]:
    """搜索指定关键词的新闻 RSS，带重试与连接复用。"""
    global _last_request_ts
    url = RSS_TEMPLATE.format(query=quote_plus(keyword))
    last_err = None
    resp = None
    for attempt in range(MAX_RETRIES + 1):
        # 简单的请求间隔节流，避免突发流量触发限流
        wait = REQUEST_INTERVAL - (time.time() - _last_request_ts)
        if wait > 0:
            time.sleep(wait)
        try:
            resp = _session.get(
                url,
                timeout=(_CONNECT_TIMEOUT, _READ_TIMEOUT),
            )
            _last_request_ts = time.time()
            resp.raise_for_status()
            return _parse_rss(resp.text)[:limit]
        except requests.RequestException as exc:
            last_err = exc
            # 4xx 客户端错误不再重试（重试只会加重限流）
            if resp is not None and 400 <= resp.status_code < 500:
                break
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_BASE * (attempt + 1))
    if last_err is not None:
        raise last_err
    return []


def _to_post(item: Dict, sector: str) -> Dict:
    link = item["link"]
    title = item["title"]
    description = item["description"]
    digest = hashlib.md5(link.encode("utf-8")).hexdigest()[:12]

    return {
        "id": f"gnews_{sector}_{digest}",
        "title": title[:100],
        "content": description[:300],
        "url": link,
        "platform": "google_news_rss",
        "author": item.get("source", "Google News"),
        "date": item.get("pub_date", ""),
        "collected_at": datetime.now().isoformat(),
    }


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有板块的公开新闻标题，作为免费补充数据源。"""
    result: Dict[str, List[Dict]] = {}

    for sector, keywords in SEARCH_KEYWORDS.items():
        posts: List[Dict] = []
        seen_links = set()

        for keyword in keywords:
            try:
                for item in search_news(keyword):
                    if item["link"] in seen_links:
                        continue
                    seen_links.add(item["link"])
                    posts.append(_to_post(item, sector))
            except requests.RequestException as exc:
                print(f"  [Google News-{sector}] 关键词 {keyword} 采集失败: {exc}")

        result[sector] = posts
        print(f"  [Google News-{sector}] 采集到 {len(posts)} 条")

    # 显式关闭 Session 释放连接池资源
    try:
        _session.close()
    except Exception:
        pass

    return result


if __name__ == "__main__":  # pragma: no cover
    data = collect_all()
    for key, value in data.items():
        print(f"{key}: {len(value)} posts")
