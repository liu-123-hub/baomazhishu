"""东方财富股吧/ETF讨论采集器 — 使用 AKShare stock_news_em 获取真实ETF相关新闻/讨论。

之前的HTML爬虫被东财反爬验证（CAPTCHA/JS校验）拦截，返回"身份核实"页面。
改为使用 AKShare 封装的东财ETF新闻接口，稳定可靠、覆盖全部25个板块。
"""
import time
import hashlib
from datetime import datetime
from typing import Dict, List

import akshare as ak


SECTOR_ETF = {
    "nasdaq":        {"name": "纳斯达克", "code": "513100"},
    "gold":          {"name": "黄金",     "code": "518880"},
    "cpo":           {"name": "CPO通信",  "code": "515880"},
    "semiconductor": {"name": "半导体",   "code": "512480"},
    "bank":          {"name": "银行",     "code": "512800"},
    "securities":    {"name": "券商",     "code": "512000"},
    "biotech":       {"name": "创新药",   "code": "159992"},
    "consumer":      {"name": "消费",     "code": "510150"},
    "newenergy":     {"name": "新能源",   "code": "516160"},
    "insurance":     {"name": "保险",     "code": "512070"},
    "baijiu":        {"name": "白酒",     "code": "512690"},
    "food":          {"name": "食品",     "code": "515080"},
    "medicine":      {"name": "医药",     "code": "512010"},
    "appliance":     {"name": "家电",     "code": "159996"},
    "tourism":       {"name": "文旅",     "code": "159766"},
    "electronics":   {"name": "电子",     "code": "159997"},
    "computer":      {"name": "计算机",   "code": "512720"},
    "communication": {"name": "通信",     "code": "515050"},
    "media":         {"name": "传媒",     "code": "512980"},
    "nonferrous":    {"name": "有色",     "code": "512400"},
    "coal":          {"name": "煤炭",     "code": "515220"},
    "chemical":      {"name": "化工",     "code": "516220"},
    "steel":         {"name": "钢铁",     "code": "515210"},
    "realestate":    {"name": "地产",     "code": "512200"},
    "infrastructure":{"name": "基建",     "code": "516950"},
}


def _to_post(row: Dict, sector: str) -> Dict:
    """将AKShare返回的新闻行转为标准post格式。"""
    title = str(row.get("新闻标题", "")).strip()[:120]
    content = str(row.get("新闻内容", "")).strip()[:300]
    url = str(row.get("新闻链接", "")).strip()
    source = str(row.get("文章来源", "东方财富")).strip()
    pub_time = str(row.get("发布时间", "")).strip()

    if not title:
        return None

    post_id = hashlib.md5((url or title).encode("utf-8")).hexdigest()[:12]

    return {
        "id": f"guba_{sector}_{post_id}",
        "title": title,
        "content": content,
        "url": url,
        "platform": "guba",
        "author": source or "东方财富财经",
        "date": pub_time,
        "collected_at": datetime.now().isoformat(),
    }


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有25个板块的ETF新闻/讨论数据。"""
    result: Dict[str, List[Dict]] = {}
    total = 0

    for sector_key, cfg in SECTOR_ETF.items():
        code = cfg["code"]
        name = cfg["name"]
        posts: List[Dict] = []

        try:
            df = ak.stock_news_em(symbol=code)
            if df is not None and not df.empty:
                for _, row in df.iterrows():
                    post = _to_post(row.to_dict(), sector_key)
                    if post:
                        posts.append(post)
            print(f"  [{name}] AKShare采集到 {len(posts)} 条新闻")
        except Exception as e:
            print(f"  [{name}] AKShare采集失败: {e}")

        result[sector_key] = posts
        total += len(posts)
        time.sleep(0.3)

    print(f"  [股吧/AKShare] 采集完成，共 {total} 条真实新闻数据")
    return result


if __name__ == "__main__":
    data = collect_all()
    for k, v in data.items():
        print(f"{k}: {len(v)} posts")
        if v:
            for p in v[:2]:
                print(f"  - {p['title'][:60]}")
