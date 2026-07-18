"""雪球社区讨论采集器，通过搜索 API 获取公开 UGC 讨论数据。"""
import hashlib
import re
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests

XUEQIU_SEARCH_URL = "https://xueqiu.com/statuses/search.json"
XUEQIU_HOME_URL = "https://xueqiu.com/"

SEARCH_COUNT = 10
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2
RETRY_DELAY = 2
REQUEST_INTERVAL = 1.5

SEARCH_KEYWORDS = {
    "nasdaq": ["纳指ETF", "纳斯达克ETF", "美股ETF"],
    "gold": ["黄金ETF", "518880", "黄金投资"],
    "cpo": ["通信ETF", "515880", "光模块"],
    "semiconductor": ["芯片ETF", "159995", "半导体ETF"],
    "bank": ["银行ETF", "512800", "银行股"],
    "securities": ["证券ETF", "512880", "券商ETF"],
    "biotech": ["创新药ETF", "159992", "医药ETF"],
    "consumer": ["消费ETF", "159928", "白酒ETF"],
    "newenergy": ["新能源ETF", "516160", "光伏ETF"],
    "insurance": ["保险ETF", "512570", "保险股"],
    "baijiu": ["白酒ETF", "512690", "酒ETF"],
    "food": ["食品ETF", "515080", "食品饮料ETF"],
    "medicine": ["医药ETF", "512010", "医疗ETF"],
    "appliance": ["家电ETF", "159996", "家电板块"],
    "tourism": ["旅游ETF", "159766", "文旅ETF"],
    "electronics": ["电子ETF", "159997", "电子板块"],
    "computer": ["计算机ETF", "512720", "计算机板块"],
    "communication": ["5G通信ETF", "515050", "通信板块"],
    "media": ["传媒ETF", "512980", "传媒板块"],
    "nonferrous": ["有色ETF", "512400", "有色金属"],
    "coal": ["煤炭ETF", "515220", "煤炭板块"],
    "chemical": ["化工ETF", "516220", "化工板块"],
    "steel": ["钢铁ETF", "515210", "钢铁板块"],
    "realestate": ["房地产ETF", "512200", "地产板块"],
    "infrastructure": ["基建ETF", "516950", "基建板块"],
}

SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "nasdaq": ["纳斯达克", "纳指", "美股", "标普", "QQQ"],
    "gold": ["黄金", "金价", "贵金属", "避险"],
    "cpo": ["CPO", "光模块", "光通信", "算力", "中际旭创", "新易盛"],
    "semiconductor": ["半导体", "芯片", "中芯国际", "北方华创", "韦尔股份"],
    "bank": ["银行", "招商银行", "工商银行", "净息差", "利差"],
    "securities": ["证券", "券商", "中信证券", "华泰证券", "东方财富"],
    "biotech": ["创新药", "医药", "CXO", "药明", "恒瑞", "百济"],
    "consumer": ["消费", "白酒", "茅台", "五粮液", "食品饮料"],
    "newenergy": ["新能源", "光伏", "锂电", "宁德时代", "比亚迪", "储能"],
    "insurance": ["保险", "中国平安", "中国人寿", "新华保险", "保险板块"],
    "baijiu": ["白酒", "茅台", "五粮液", "泸州老窖", "汾酒", "酒鬼酒"],
    "food": ["食品", "调味品", "伊利", "海天味业", "中炬高新", "食品饮料"],
    "medicine": ["医药", "医疗", "恒瑞医药", "药明康德", "迈瑞医疗", "医药板块"],
    "appliance": ["家电", "美的", "格力", "海尔", "家电板块", "白色家电"],
    "tourism": ["旅游", "文旅", "中国中免", "宋城演艺", "旅游板块", "免税"],
    "electronics": ["电子", "消费电子", "立讯精密", "歌尔股份", "电子板块", "苹果产业链"],
    "computer": ["计算机", "软件", "金山办公", "中科曙光", "计算机板块", "信创"],
    "communication": ["通信", "5G", "中兴通讯", "烽火通信", "通信板块", "运营商"],
    "media": ["传媒", "游戏", "三七互娱", "完美世界", "传媒板块", "影视"],
    "nonferrous": ["有色", "铜", "铝", "锂", "紫金矿业", "有色金属", "洛阳钼业"],
    "coal": ["煤炭", "动力煤", "焦煤", "中国神华", "陕西煤业", "煤炭板块"],
    "chemical": ["化工", "万华化学", "荣盛石化", "恒力石化", "化工板块", "新材料"],
    "steel": ["钢铁", "宝钢股份", "鞍钢股份", "钢铁板块", "钢材", "铁矿石"],
    "realestate": ["地产", "房地产", "万科", "保利发展", "招商蛇口", "地产板块"],
    "infrastructure": ["基建", "建筑", "中国建筑", "中国交建", "中国铁建", "基建板块"],
}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}


class XueqiuSession:
    """雪球 Session 管理器，自动获取并维护 Cookie（30分钟复用）。"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self._cookie_obtained = False
        self._cookie_time = None

    def _ensure_cookie(self) -> bool:
        """确保 session 持有有效 Cookie（30 分钟内复用）。"""
        if self._cookie_obtained and self._cookie_time:
            if (datetime.now() - self._cookie_time).seconds < 1800:
                return True
        try:
            resp = self.session.get(
                XUEQIU_HOME_URL,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            resp.raise_for_status()
            self._cookie_obtained = True
            self._cookie_time = datetime.now()
            return True
        except Exception as e:
            print(f"  [雪球] 获取 Cookie 失败: {e}")
            return False

    def search(self, keyword: str, count: int = SEARCH_COUNT) -> List[Dict]:
        """搜索雪球帖子，返回帖子列表。"""
        if not self._ensure_cookie():
            return []

        params = {
            "count": count,
            "comment": 0,
            "symbol": "",
            "hl": 0,
            "source": "all",
            "sort": "time",
            "q": keyword,
            "page": 1,
        }

        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self.session.get(
                    XUEQIU_SEARCH_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
                resp.raise_for_status()
                data = resp.json()
                items = data.get("list", [])
                return items
            except requests.RequestException as e:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  [雪球] 搜索「{keyword}」失败: {e}")
                    return []
            except json.JSONDecodeError as e:
                print(f"  [雪球] 搜索「{keyword}」响应解析失败: {e}")
                return []

        return []


_xq_session: Optional[XueqiuSession] = None


def _get_session() -> XueqiuSession:
    global _xq_session
    if _xq_session is None:
        _xq_session = XueqiuSession()
    return _xq_session


def _clean_html(raw: str) -> str:
    """清除 HTML 标签，返回纯文本。"""
    if not raw:
        return ""
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_post(item: Dict, sector: str) -> Optional[Dict]:
    """将雪球 API 返回的帖子转为项目标准格式。"""
    if not isinstance(item, dict):
        return None

    post_id = str(item.get("id", ""))
    if not post_id:
        return None

    title = _clean_html(item.get("title", "") or item.get("text", ""))[:100]
    content = _clean_html(item.get("text", "") or item.get("description", ""))[:300]
    user_info = item.get("user", {})

    if not title and not content:
        return None

    return {
        "id": f"xq_{sector}_{post_id}",
        "title": title,
        "content": content,
        "url": f"https://xueqiu.com{item.get('target', '')}",
        "platform": "xueqiu",
        "author": (user_info.get("screen_name") or user_info.get("name") or "雪球用户") if isinstance(user_info, dict) else "雪球用户",
        "author_followers": user_info.get("followers_count", 0) if isinstance(user_info, dict) else 0,
        "likes": item.get("like_count", 0),
        "comments_count": item.get("reply_count", 0) or item.get("comment_count", 0),
        "date": datetime.fromtimestamp(
            item.get("created_at", 0) / 1000
        ).isoformat() if item.get("created_at") else "",
        "collected_at": datetime.now().isoformat(),
    }


def _classify_sector(title: str, content: str) -> Optional[str]:
    """根据标题和内容关键词归类到板块。"""
    combined = f"{title} {content}"

    for sector, keywords in SECTOR_KEYWORDS.items():
        for kw in keywords:
            if kw in title or kw in content:
                return sector
        for kw in keywords:
            if kw in combined:
                return sector

    return None


ALL_SECTORS = list(SEARCH_KEYWORDS.keys())


def _empty_result() -> Dict[str, List[Dict]]:
    return {s: [] for s in ALL_SECTORS}


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有板块雪球社区讨论，ETF关键词搜索+二次归类。"""
    result: Dict[str, List[Dict]] = _empty_result()
    seen_ids: set = set()

    print("  [雪球社区] 开始采集真实讨论数据...")

    session = _get_session()
    if not session._ensure_cookie():
        print("  [雪球社区] ⚠️ 无法获取Cookie，跳过采集（雪球WAF需要登录）")
        return result

    test_items = session.search("银行ETF", count=3)
    if not test_items:
        print("  [雪球社区] ⚠️ 搜索API被WAF拦截(400016)，需要登录账号，跳过采集")
        return result

    total_count = 0

    for sector, keywords in SEARCH_KEYWORDS.items():
        sector_posts = []
        for kw in keywords:
            items = session.search(kw, count=SEARCH_COUNT)
            for item in items:
                parsed = _parse_post(item, sector)
                if parsed is None:
                    continue
                pid = parsed["id"]
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                sector_posts.append(parsed)
            time.sleep(REQUEST_INTERVAL)

        result[sector] = sector_posts
        total_count += len(sector_posts)
        if sector_posts:
            print(f"  [雪球-{sector}] 采集到 {len(sector_posts)} 条讨论")

    print(f"  [雪球社区] 采集完成，共 {total_count} 条真实讨论")
    return result


if __name__ == "__main__":  # pragma: no cover
    data = collect_all()
    for key, value in data.items():
        print(f"{key}: {len(value)} posts")
        for post in value[:2]:
            print(f"  - {post.get('title', '')[:60]}")
