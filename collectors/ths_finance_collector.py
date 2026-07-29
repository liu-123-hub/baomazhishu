"""同花顺财经新闻采集器，HTML 解析公开新闻并按板块分类。"""
import os
import sys
from typing import Dict, List
from urllib.parse import urlparse
import re
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from collectors.common import (
    classify_sector,
    empty_sector_result,
    fetch_html_page,
    make_post,
    parse_html_links,
)

NEWS_PAGES = [
    "http://news.10jqka.com.cn/cjkx_list/",
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

SKIP_KEYWORDS = ["首页", "登录", "注册", "下载", "更多", "返回", "网站地图",
                 "查看", "关于", "联系"]

_LINK_PATTERN = re.compile(
    r'<a[^>]*href="(https?://[^"]*10jqka\.com\.cn[^"]*shtml)"[^>]*>([^<]{8,120})</a>',
    re.IGNORECASE,
)


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有新闻页面，按板块关键词分类后返回。"""
    result = empty_sector_result(SECTOR_KEYWORDS)
    seen_links: set = set()

    for page_url in NEWS_PAGES:
        html_text = fetch_html_page(
            page_url, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY_BASE, "[同花顺]"
        )
        if html_text is None:
            continue

        items = parse_html_links(html_text, _LINK_PATTERN, SKIP_KEYWORDS, "同花顺财经")[:MAX_ITEMS_PER_PAGE]

        matched_count = 0
        for item in items:
            link = item.get("link", "")
            if link in seen_links:
                continue

            sector = classify_sector(item["title"], item.get("description", ""), SECTOR_KEYWORDS)
            if sector is None:
                continue

            seen_links.add(link)
            result[sector].append(
                make_post(item, sector, "ths_finance", "ths", "同花顺财经")
            )
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
