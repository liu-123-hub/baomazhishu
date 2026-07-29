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

from collectors.common import (
    classify_sector,
    empty_sector_result,
    fetch_html_page,
    make_post,
    parse_html_links,
)

NEWS_PAGES = [
    "https://finance.eastmoney.com/a/cgsxw.html",
]

REQUEST_TIMEOUT = 15
MAX_ITEMS_PER_PAGE = 60
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "nasdaq": ["纳斯达克", "纳指", "美股", "美科技", "纳指ETF", "标普500", "QQQ",
               "513100", "159941", "中概互联", "美国科技"],
    "gold": ["黄金", "金价", "贵金属", "金条", "黄金ETF", "金价下跌", "金价上涨",
             "518880", "博时黄金", "黄金基金", "避险"],
    "cpo": ["CPO", "光模块", "通信ETF", "5G通信", "光通信", "算力",
            "515880", "中际旭创", "新易盛", "光迅科技", "AI算力"],
    "semiconductor": ["半导体", "芯片", "集成电路", "芯片ETF", "半导体ETF", "AI芯片",
                      "国产芯片", "512480", "中芯国际", "北方华创", "科创板芯片"],
    "bank": ["银行", "银行ETF", "银行股", "银行业", "大行", "股份行", "城商行",
             "512800", "招商银行", "工商银行", "净息差", "利差", "银行板块"],
    "securities": ["证券", "证券ETF", "券商", "券商股", "证券公司", "512000",
                   "中信证券", "华泰证券", "东方财富", "牛市旗手", "券商板块"],
    "biotech": ["创新药", "生物医药", "医药ETF", "创新药ETF", "159992", "医药",
                "生物科技", "CXO", "药明", "恒瑞医药", "医疗器械", "医药股"],
    "consumer": ["消费", "消费ETF", "消费股", "白酒", "食品饮料", "510150",
                 "茅台", "五粮液", "必选消费", "可选消费", "消费板块"],
    "newenergy": ["新能源", "新能源ETF", "光伏", "锂电", "新能源车", "516160",
                  "宁德时代", "比亚迪", "碳酸锂", "储能", "风电", "新能源板块"],
    "insurance": ["保险", "保险ETF", "512570", "中国平安", "中国人寿", "新华保险",
                  "保险板块", "保险股", "保费"],
    "baijiu": ["白酒", "酒ETF", "512690", "茅台", "五粮液", "泸州老窖",
               "汾酒", "酒鬼酒", "白酒板块", "高端白酒"],
    "food": ["食品", "食品ETF", "515080", "调味品", "伊利", "海天味业",
             "中炬高新", "食品饮料", "食品板块", "乳业"],
    "medicine": ["医药", "医疗ETF", "512010", "医疗", "恒瑞医药", "药明康德",
                 "迈瑞医疗", "医药板块", "医疗服务", "医疗器械"],
    "appliance": ["家电", "家电ETF", "159996", "美的", "格力", "海尔",
                  "家电板块", "白色家电", "小家电", "家电股"],
    "tourism": ["旅游", "旅游ETF", "159766", "文旅", "中国中免", "宋城演艺",
                "旅游板块", "免税", "酒店", "景区"],
    "electronics": ["电子", "电子ETF", "159997", "消费电子", "立讯精密", "歌尔股份",
                    "电子板块", "苹果产业链", "面板", "摄像头"],
    "computer": ["计算机", "计算机ETF", "512720", "软件", "金山办公", "中科曙光",
                 "计算机板块", "信创", "操作系统", "ERP"],
    "communication": ["通信", "5G通信ETF", "515050", "5G", "中兴通讯", "烽火通信",
                      "通信板块", "运营商", "中国联通", "中国移动"],
    "media": ["传媒", "传媒ETF", "512980", "游戏", "三七互娱", "完美世界",
              "传媒板块", "影视", "广告", "直播"],
    "nonferrous": ["有色", "有色ETF", "512400", "铜", "铝", "锂",
                   "紫金矿业", "有色金属", "洛阳钼业", "稀有金属"],
    "coal": ["煤炭", "煤炭ETF", "515220", "动力煤", "焦煤", "中国神华",
             "陕西煤业", "煤炭板块", "煤价", "煤炭股"],
    "chemical": ["化工", "化工ETF", "516220", "万华化学", "荣盛石化", "恒力石化",
                 "化工板块", "新材料", "聚氨酯", "烯烃"],
    "steel": ["钢铁", "钢铁ETF", "515210", "宝钢股份", "鞍钢股份",
              "钢铁板块", "钢材", "铁矿石", "螺纹钢"],
    "realestate": ["地产", "房地产ETF", "512200", "房地产", "万科", "保利发展",
                   "招商蛇口", "地产板块", "楼市", "物业"],
    "infrastructure": ["基建", "基建ETF", "516950", "建筑", "中国建筑", "中国交建",
                       "中国铁建", "基建板块", "建材", "工程机械"],
}

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

            sector = classify_sector(item["title"], item.get("description", ""), SECTOR_KEYWORDS)
            if sector is None:
                continue

            seen_links.add(link)
            result[sector].append(
                make_post(item, sector, "eastmoney_news", "em", "东方财富资讯")
            )
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
