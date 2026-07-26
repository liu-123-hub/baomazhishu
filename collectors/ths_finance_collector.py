"""同花顺财经新闻采集器，HTML 解析公开新闻并按板块分类。

数据源：同花顺(10jqka.com.cn)公开新闻页面，真实公开财经资讯。
"""
import hashlib
import html
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

NEWS_PAGES = [
    # 财经即时新闻：返回 field.10jqka.com.cn 域名的板块相关新闻，命中率高
    "http://news.10jqka.com.cn/cjkx_list/",
    # 股票频道首页：返回 stock.10jqka.com.cn 域名的个股/板块新闻
    "http://stock.10jqka.com.cn/",
]

REQUEST_TIMEOUT = 15
MAX_ITEMS_PER_PAGE = 80
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "nasdaq": ["纳斯达克", "纳指", "美股", "美科技", "纳指ETF", "标普500",
               "中概股", "美国股市", "科技股"],
    "gold": ["黄金", "金价", "贵金属", "金条", "黄金ETF", "金价下跌", "金价上涨",
             "黄金基金", "避险资产", "黄金走势"],
    "cpo": ["CPO", "光模块", "通信ETF", "5G通信", "光通信", "算力",
            "AI算力", "数据中心", "通信设备"],
    "semiconductor": ["半导体", "芯片", "集成电路", "芯片ETF", "半导体ETF", "AI芯片",
                      "国产芯片", "芯片制造", "半导体设备", "中芯国际"],
    "bank": ["银行", "银行ETF", "银行股", "银行业", "大行", "股份行", "城商行",
             "招商银行", "工商银行", "净息差", "利差", "银行板块"],
    "securities": ["证券", "证券ETF", "券商", "券商股", "证券公司",
                   "中信证券", "华泰证券", "牛市旗手", "券商板块"],
    "biotech": ["创新药", "生物医药", "医药ETF", "创新药ETF", "医药",
                "生物科技", "CXO", "药明", "恒瑞医药", "医疗器械", "医药股"],
    "consumer": ["消费", "消费ETF", "消费股", "白酒", "食品饮料",
                 "茅台", "五粮液", "必选消费", "可选消费", "消费板块"],
    "newenergy": ["新能源", "新能源ETF", "光伏", "锂电", "新能源车",
                  "宁德时代", "比亚迪", "碳酸锂", "储能", "风电", "新能源板块"],
    "insurance": ["保险", "保险ETF", "中国平安", "中国人寿", "新华保险", "保险板块"],
    "baijiu": ["白酒", "酒ETF", "茅台", "五粮液", "泸州老窖", "汾酒", "白酒板块"],
    "food": ["食品", "食品ETF", "调味品", "伊利", "海天味业", "食品饮料", "食品板块"],
    "medicine": ["医药", "医疗ETF", "医疗", "恒瑞医药", "药明康德", "迈瑞医疗", "医药板块"],
    "appliance": ["家电", "家电ETF", "美的", "格力", "海尔", "家电板块"],
    "tourism": ["旅游", "旅游ETF", "文旅", "中国中免", "宋城演艺", "旅游板块", "免税"],
    "electronics": ["电子", "电子ETF", "消费电子", "立讯精密", "歌尔股份", "电子板块"],
    "computer": ["计算机", "计算机ETF", "软件", "金山办公", "中科曙光", "计算机板块", "信创"],
    "communication": ["通信", "5G通信ETF", "5G", "中兴通讯", "烽火通信", "通信板块"],
    "media": ["传媒", "传媒ETF", "游戏", "三七互娱", "完美世界", "传媒板块", "影视"],
    "nonferrous": ["有色", "有色ETF", "铜", "铝", "锂", "紫金矿业", "有色金属"],
    "coal": ["煤炭", "煤炭ETF", "动力煤", "焦煤", "中国神华", "陕西煤业", "煤炭板块"],
    "chemical": ["化工", "化工ETF", "万华化学", "荣盛石化", "恒力石化", "化工板块"],
    "steel": ["钢铁", "钢铁ETF", "宝钢股份", "鞍钢股份", "钢铁板块", "铁矿石"],
    "realestate": ["地产", "房地产ETF", "房地产", "万科", "保利发展", "地产板块"],
    "infrastructure": ["基建", "基建ETF", "建筑", "中国建筑", "中国交建", "基建板块"],
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
}

_LINK_PATTERN = re.compile(
    r'<a[^>]*href="(https?://[^"]*10jqka\.com\.cn[^"]*shtml)"[^>]*>([^<]{8,120})</a>',
    re.IGNORECASE,
)


def _clean_html(raw_html: str) -> str:
    """清除 HTML 标签并反转义实体，返回纯文本。"""
    text = re.sub(r"<[^>]+>", " ", raw_html or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_html(html_text: str) -> List[Dict]:
    """从 HTML 页面中提取新闻标题和链接。"""
    items: List[Dict] = []
    seen_links: set = set()

    for match in _LINK_PATTERN.finditer(html_text):
        link = match.group(1).strip()
        title = _clean_html(match.group(2))

        if not title or len(title) < 8:
            continue
        skip_keywords = ["首页", "登录", "注册", "下载", "更多", "返回", "网站地图",
                         "查看", "关于", "联系"]
        if any(sk in title for sk in skip_keywords):
            continue

        if link in seen_links:
            continue
        seen_links.add(link)

        items.append({
            "title": title,
            "link": link,
            "description": "",
            "source": "同花顺财经",
            "pub_date": "",
        })

    return items


def _classify_sector(title: str, description: str) -> Optional[str]:
    """根据标题关键词匹配，将新闻归入对应板块。"""
    combined = f"{title} {description}"

    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in title:
                return sector
        for kw in keywords:
            if kw in combined:
                return sector

    return None


def _to_post(item: Dict, sector: str) -> Dict:
    """将新闻 item 转为项目统一的 post 字典格式。"""
    link = item["link"]
    title = item["title"]
    digest = hashlib.md5(link.encode("utf-8")).hexdigest()[:12]

    return {
        "id": f"ths_{sector}_{digest}",
        "title": title[:100],
        "content": item.get("description", "")[:300],
        "url": link,
        "platform": "ths_finance",
        "author": item.get("source", "同花顺财经"),
        "date": item.get("pub_date", ""),
        "collected_at": datetime.now().isoformat(),
    }


def _empty_result() -> Dict[str, List[Dict]]:
    """生成包含所有25个板块的空结果字典。"""
    return {sector: [] for sector in SECTOR_KEYWORDS}


def fetch_page(url: str, timeout: int = REQUEST_TIMEOUT) -> Optional[str]:
    """获取页面 HTML 文本，带重试机制。

    编码策略：同花顺页面使用 GBK 编码，不能用 utf-8 强制解码。
    优先使用响应头声明的 charset；若无则用 chardet 自动检测（apparent_encoding）。
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
            resp.raise_for_status()
            # 服务器未声明编码或 requests fallback 到 ISO-8859-1 时，自动检测
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding
            return resp.text

        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
            else:
                print(f"    [同花顺] 请求超时（已重试{MAX_RETRIES}次）: {url}")

        except requests.exceptions.ConnectionError as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
            else:
                print(f"    [同花顺] 连接失败（已重试{MAX_RETRIES}次）: {e}")

        except requests.exceptions.HTTPError:
            status = resp.status_code if hasattr(resp, "status_code") else "N/A"
            if isinstance(status, int) and 400 <= status < 500:
                print(f"    [同花顺] HTTP {status} 客户端错误，跳过: {url}")
                break
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY_BASE * (attempt + 1))
            else:
                print(f"    [同花顺] HTTP {status} 服务端错误，已重试 {MAX_RETRIES} 次仍失败: {url}")

    return None


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有新闻页面，按板块关键词分类后返回。"""
    result: Dict[str, List[Dict]] = _empty_result()
    seen_links: set = set()

    for page_url in NEWS_PAGES:
        html_text = fetch_page(page_url)
        if html_text is None:
            continue

        items = _parse_html(html_text)[:MAX_ITEMS_PER_PAGE]

        matched_count = 0
        for item in items:
            link = item.get("link", "")
            if link in seen_links:
                continue

            sector = _classify_sector(item["title"], item.get("description", ""))
            if sector is None:
                continue

            seen_links.add(link)
            result[sector].append(_to_post(item, sector))
            matched_count += 1

        print(f"  [同花顺] {urlparse(page_url).path} 共 {len(items)} 条，命中板块 {matched_count} 条")
        time.sleep(1)

    for sector, posts in result.items():
        if posts:
            print(f"  [同花顺-{sector}] 采集到 {len(posts)} 条")

    return result


if __name__ == "__main__":  # pragma: no cover
    data = collect_all()
    for key, value in data.items():
        print(f"{key}: {len(value)} posts")
