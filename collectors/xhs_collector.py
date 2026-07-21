"""小红书数据采集器，通过 rnote.dev API 获取真实笔记数据。"""
import os
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional

API_KEY = os.environ.get("RNODE_API_KEY", "")
API_BASE = "https://rnote.dev/api/v2"
_PROXY_URL = os.environ.get("MOM_INDEX_PROXY_URL", "http://127.0.0.1:7890")
PROXY = {"http": _PROXY_URL, "https": _PROXY_URL} if os.environ.get("MOM_INDEX_PROXY", "") == "1" else None

MAX_RETRIES = 2
RETRY_DELAY = 2

SEARCH_KEYWORDS = {
    "nasdaq":     ["美股怎么买", "纳斯达克新手", "纳指还能买吗", "买美股"],
    "gold":       ["黄金怎么买", "买黄金亏了", "黄金新手", "黄金还能涨吗"],
    "cpo":        ["CPO是什么", "光模块还能涨吗", "通信ETF"],
    "semiconductor": ["芯片还能买吗", "半导体新手", "芯片ETF"],
    "bank":       ["银行ETF怎么买", "银行股新手", "银行还能涨吗", "银行亏了"],
    "securities": ["证券ETF新手", "券商还能买吗", "证券亏了", "券商入门"],
    "biotech":    ["创新药怎么买", "医药ETF新手", "创新药还能涨吗", "医药亏了"],
    "consumer":   ["消费ETF怎么买", "白酒新手", "消费股还能买吗", "消费亏了"],
    "newenergy":  ["新能源怎么买", "光伏新手", "新能源还能涨吗", "新能源亏了"],
    "insurance":  ["保险怎么买", "保险股", "平安保险"],
    "baijiu":     ["白酒基金", "白酒还能涨吗", "茅台股票"],
    "food":       ["食品饮料基金", "消费基金怎么买"],
    "medicine":   ["医药基金怎么买", "医疗基金", "医药还能涨吗"],
    "appliance":  ["家电板块", "家电基金"],
    "tourism":    ["旅游基金", "文旅板块", "免税概念"],
    "electronics": ["消费电子基金", "电子ETF"],
    "computer":   ["计算机ETF", "信创基金", "软件股"],
    "communication": ["5G基金", "通信板块"],
    "media":      ["游戏基金", "传媒ETF", "影视股"],
    "nonferrous": ["有色金属基金", "铜价", "锂矿"],
    "coal":       ["煤炭基金", "煤炭股", "煤价"],
    "chemical":   ["化工基金", "化工板块"],
    "steel":      ["钢铁板块", "钢铁ETF"],
    "realestate": ["地产基金", "房地产板块", "楼市"],
    "infrastructure": ["基建基金", "基建板块"],
}

ALL_SECTORS = list(SEARCH_KEYWORDS.keys())


def _retry_request(func, *args, **kwargs):
    """带重试机制的请求封装。"""
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
    """搜索小红书笔记，带重试机制。"""
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
    """获取笔记详情（含评论），带重试机制。"""
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
    """标准化笔记格式，适配 rnote.dev API 返回结构。"""
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
    """返回空的板块数据结构，覆盖全部25个板块。"""
    return {s: [] for s in ALL_SECTORS}


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有板块的小红书真实数据，未配置API Key时返回空数据。"""
    result = _empty_sector_result()
    
    if not API_KEY:
        print("  ⚠️ 未配置 RNODE_API_KEY，小红书数据源未启用（返回空数据）")
        print("  💡 如需启用小红书数据，请设置环境变量: set RNODE_API_KEY=your_key")
        return result
    
    print("  [小红书] 开始从 rnote.dev API 采集真实数据...")
    
    total_count = 0
    for sector_key, keywords in SEARCH_KEYWORDS.items():
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
