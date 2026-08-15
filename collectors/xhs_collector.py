import os
import sys
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analyzer.sector_keywords import get_all_sector_keywords

SECTOR_KEYWORDS: Dict[str, List[str]] = get_all_sector_keywords()
ALL_SECTORS: List[str] = list(SECTOR_KEYWORDS.keys())

API_KEY = os.environ.get("RNODE_API_KEY", "")
API_BASE = "https://rnote.dev/api/v2"
_PROXY_URL = os.environ.get("MOM_INDEX_PROXY_URL", "http://127.0.0.1:7890")
PROXY = {"http": _PROXY_URL, "https": _PROXY_URL} if os.environ.get("MOM_INDEX_PROXY", "") == "1" else None

MAX_RETRIES = 2
RETRY_DELAY = 2

SEARCH_KEYWORDS = {
    "bank":       ["银行ETF怎么买", "银行股新手", "银行还能涨吗", "银行亏了"],
    "securities": ["证券ETF新手", "券商还能涨吗", "证券亏了", "券商入门"],
    "insurance":  ["保险怎么买", "保险股", "平安保险"],
    "baijiu":     ["白酒基金", "白酒还能涨吗", "茅台股票"],
    "food":       ["食品饮料基金", "消费基金怎么买"],
    "medicine":   ["医药基金怎么买", "医疗基金", "医药还能涨吗"],
    "appliance":  ["家电板块", "家电基金"],
    "tourism":    ["旅游基金", "文旅板块", "免税概念"],
    "biotech":    ["创新药怎么买", "医药ETF新手", "创新药还能涨吗", "生物医药亏了"],
    "consumer":   ["消费ETF怎么买", "大消费新手", "消费股还能买吗", "消费亏了"],
    "semiconductor": ["芯片还能买吗", "半导体新手", "芯片ETF"],
    "electronics": ["消费电子基金", "电子ETF"],
    "ai_computing": ["AI算力基金", "算力ETF", "人工智能怎么买", "GPU股票"],
    "cpo":        ["CPO是什么", "光模块还能涨吗", "通信ETF"],
    "computer":   ["计算机ETF", "信创基金", "软件股"],
    "communication": ["5G基金", "通信板块"],
    "military":   ["军工基金", "军工板块", "军工还能涨吗"],
    "robot":      ["机器人基金", "人形机器人股票", "减速器板块"],
    "media":      ["游戏基金", "传媒ETF", "影视股"],
    "coal":       ["煤炭基金", "煤炭股", "煤价"],
    "crude_oil":  ["原油基金", "石油怎么买", "油价上涨", "原油亏了"],
    "newenergy":  ["新能源怎么买", "光伏新手", "新能源还能涨吗", "新能源亏了"],
    "battery":    ["锂电池基金", "电池ETF怎么买", "宁德时代", "固态电池"],
    "power_grid": ["电网设备", "特高压基金", "电力基建", "智能电网"],
    "infrastructure": ["基建基金", "基建板块"],
    "nonferrous": ["有色金属基金", "铜价", "锂矿"],
    "chemical":   ["化工基金", "化工板块"],
    "steel":      ["钢铁板块", "钢铁ETF"],
    "realestate": ["地产基金", "房地产板块", "楼市"],
    "nasdaq":     ["美股怎么买", "纳斯达克新手", "纳指还能买吗", "买美股"],
    "gold":       ["黄金怎么买", "买黄金亏了", "黄金新手", "黄金还能涨吗"],
}


def _retry_request(func, *args, **kwargs):
    last_exception = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            return func(*args, **kwargs)
        except (requests.RequestException, requests.Timeout) as e:
            last_exception = e
            if attempt < MAX_RETRIES:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"  [小红书] 请求失败（第{attempt + 1}次），{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"  [小红书] 请求失败（已重试{MAX_RETRIES}次）: {e}")
    raise last_exception


def search_notes(keyword: str, count: int = 20) -> List[Dict]:
    if not API_KEY:
        print(f"  ⚠️ 未配置 RNODE_API_KEY，跳过小红书搜索: {keyword}")
        return []
    
    try:
        def _do_request():
            resp = requests.get(
                f"{API_BASE}/crawler/search/notes",
                params={"keyword": keyword, "count": count, "sort": "general"},
                headers={"X-API-Key": API_KEY, "User-Agent": "mom-index/1.0"},
                proxies=PROXY,
                timeout=15,
            )
            resp.raise_for_status()
            return resp
        
        resp = _retry_request(_do_request)
        data = resp.json()
        inner = data.get("data", {}).get("data", {})
        items = inner.get("items", [])
        notes = []
        for item in items:
            note = item.get("note") or item.get("note_card") or item
            if note and isinstance(note, dict):
                parsed = _parse_note(note)
                if parsed and parsed.get("id"):
                    notes.append(parsed)
        return notes
    except Exception as e:
        print(f"  [小红书] 搜索「{keyword}」失败: {e}")
        return []


def get_note_detail(note_id: str) -> Optional[Dict]:
    if not API_KEY:
        return None
    try:
        def _do_request():
            resp = requests.get(
                f"{API_BASE}/crawler/note/image",
                params={"note_id": note_id},
                headers={"X-API-Key": API_KEY},
                proxies=PROXY,
                timeout=15,
            )
            resp.raise_for_status()
            return resp
        
        resp = _retry_request(_do_request)
        return resp.json()
    except Exception as e:
        print(f"  [小红书] 详情请求失败 {note_id}: {e}")
        return None


def _parse_note(raw: Dict) -> Optional[Dict]:
    if not isinstance(raw, dict):
        return None
    
    user = raw.get("user") or raw.get("author") or {}
    interact = raw.get("interact_info") or raw.get("note_interact_info") or {}
    tags = raw.get("tag_list") or raw.get("tags") or []
    
    note_id = raw.get("id") or raw.get("note_id", "")
    if not note_id:
        return None
    
    title = (raw.get("title") or raw.get("desc") or "")[:100]
    content = raw.get("desc") or raw.get("content") or ""
    
    if not title and not content:
        return None
    
    if not isinstance(user, dict):
        user = {}
    if not isinstance(interact, dict):
        interact = {}
    if not isinstance(tags, list):
        tags = []
    
    return {
        "id": str(note_id),
        "title": title,
        "content": content,
        "platform": "xiaohongshu",
        "author": user.get("nickname") or user.get("nick_name", "未知"),
        "author_followers": interact.get("follower_count", 0) if isinstance(interact, dict) else 0,
        "likes": interact.get("liked_count", 0) if isinstance(interact, dict) else 0,
        "comments_count": interact.get("comment_count", 0) if isinstance(interact, dict) else 0,
        "collected_at": datetime.now().isoformat(),
        "tags": [t.get("name", t) if isinstance(t, dict) else t for t in tags],
    }


def _empty_sector_result() -> Dict[str, List[Dict]]:
    return {s: [] for s in ALL_SECTORS}


def collect_all() -> Dict[str, List[Dict]]:
    result = _empty_sector_result()
    
    if not API_KEY:
        print("  ⚠️ 未配置 RNODE_API_KEY，小红书数据源未启用（返回空数据）")
        print("  💡 如需启用小红书数据，请设置环境变量: set RNODE_API_KEY=your_key")
        return result
    
    print("  [小红书] 开始从 rnote.dev API 采集真实数据...")
    
    total_count = 0
    for sector_key in ALL_SECTORS:
        keywords = SEARCH_KEYWORDS.get(sector_key, [sector_key])
        all_notes = []
        for kw in keywords:
            notes = search_notes(kw, count=5)
            all_notes.extend(notes)
            time.sleep(0.5)
        
        seen = set()
        unique = []
        for n in all_notes:
            nid = n.get("id", "")
            if nid and nid not in seen:
                seen.add(nid)
                unique.append(n)
        
        result[sector_key] = unique
        total_count += len(unique)
        print(f"  [小红书-{sector_key}] 采集到 {len(unique)} 条真实笔记")
    
    print(f"  [小红书] 采集完成，共 {total_count} 条真实数据")
    return result


if __name__ == "__main__":
    if not API_KEY:
        print("请先设置 RNODE_API_KEY 环境变量")
        print("注册地址: https://rnote.dev/auth/register")
    else:
        data = collect_all()
        for k, v in data.items():
            print(f"{k}: {len(v)} posts")
