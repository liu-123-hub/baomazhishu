"""东方财富股吧/ETF讨论采集器，使用AKShare获取ETF相关新闻。

板块分类 v2.0：覆盖所有30个板块，概念赛道使用代理ETF。
"""
import os
import sys
import time
import hashlib
from datetime import datetime
from typing import Dict, List

import akshare as ak

# 导入项目根目录，以便从analyzer导入核心配置
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from analyzer.index_calculator import SECTOR_NAMES

# ============================================================
# 板块→ETF代码映射（与 market_data_collector.py 保持一致）
# ============================================================
SECTOR_ETF = {
    # ── T1 第一梯队：AI算力硬科技 ──
    "semiconductor":  {"name": "半导体",   "code": "159995"},
    "electronics":    {"name": "电子",     "code": "159997"},
    "ai_computing":   {"name": "AI算力",   "code": "159819"},  # 人工智能ETF代理
    "cpo":            {"name": "CPO光通信","code": "515880"},  # 通信ETF代理
    # ── T2 第二梯队：高端制造/智能科技 ──
    "computer":       {"name": "计算机",   "code": "512720"},
    "communication":  {"name": "通信",     "code": "515050"},
    "military":       {"name": "军工",     "code": "512660"},
    "robot":          {"name": "机器人",   "code": "562500"},
    # ── T3 第三梯队：新能源/电力设备 ──
    "newenergy":      {"name": "新能源",   "code": "516160"},
    "battery":        {"name": "电池",     "code": "159755"},
    "power_grid":     {"name": "电力设备", "code": "159611"},
    # ── T4 第四梯队：消费医疗/文化传媒 ──
    "medicine":       {"name": "医药",     "code": "512010"},
    "baijiu":         {"name": "白酒",     "code": "512690"},
    "food":           {"name": "食品饮料", "code": "515080"},
    "appliance":      {"name": "家电",     "code": "159996"},
    "tourism":        {"name": "文旅",     "code": "159766"},
    "media":          {"name": "传媒",     "code": "512980"},
    "biotech":        {"name": "创新药",   "code": "159992"},
    "consumer":       {"name": "大消费",   "code": "159928"},
    # ── V1 价值防御：大金融 ──
    "bank":           {"name": "银行",     "code": "512800"},
    "securities":     {"name": "券商",     "code": "512880"},
    "insurance":      {"name": "保险",     "code": "512570"},
    # ── V2 价值防御：周期资源 ──
    "coal":           {"name": "煤炭",     "code": "515220"},
    "crude_oil":      {"name": "石油石化", "code": "501018"},
    "nonferrous":     {"name": "有色金属", "code": "512400"},
    "chemical":       {"name": "化工",     "code": "516220"},
    "steel":          {"name": "钢铁",     "code": "515210"},
    # ── V3 价值防御：基建地产 ──
    "infrastructure": {"name": "基建",     "code": "516950"},
    "realestate":     {"name": "房地产",   "code": "512200"},
    # ── DEF 防御资产/海外 ──
    "gold":           {"name": "黄金",     "code": "518880"},
    "nasdaq":         {"name": "纳斯达克", "code": "513100"},
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
    """采集所有25个板块的ETF新闻/讨论数据，带重试。"""
    result: Dict[str, List[Dict]] = {}
    total = 0
    MAX_RETRIES = 2
    RETRY_BACKOFF = 1.0

    for sector_key, cfg in SECTOR_ETF.items():
        code = cfg["code"]
        name = cfg["name"]
        posts: List[Dict] = []

        for attempt in range(MAX_RETRIES + 1):
            try:
                df = ak.stock_news_em(symbol=code)
                if df is not None and not df.empty:
                    for _, row in df.iterrows():
                        post = _to_post(row.to_dict(), sector_key)
                        if post:
                            posts.append(post)
                print(f"  [{name}] AKShare采集到 {len(posts)} 条新闻")
                break
            except Exception as e:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_BACKOFF * (attempt + 1))
                else:
                    print(f"  [{name}] AKShare采集失败（已重试{MAX_RETRIES}次）: {e}")

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
