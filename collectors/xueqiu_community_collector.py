"""雪球社区讨论采集器，通过搜索 API 获取公开 UGC 讨论数据。"""
import os
import sys
from typing import Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from analyzer.sector_keywords import get_all_sector_keywords

SECTOR_KEYWORDS: Dict[str, List[str]] = get_all_sector_keywords()
ALL_SECTORS: List[str] = list(SECTOR_KEYWORDS.keys())

SEARCH_KEYWORDS = {
    "bank": ["银行ETF", "512800", "银行股"],
    "securities": ["证券ETF", "512880", "券商ETF"],
    "insurance": ["保险ETF", "512570", "保险股"],
    "baijiu": ["白酒ETF", "512690", "酒ETF"],
    "food": ["食品ETF", "515080", "食品饮料ETF"],
    "medicine": ["医药ETF", "512010", "医疗ETF"],
    "appliance": ["家电ETF", "159996", "家电板块"],
    "tourism": ["旅游ETF", "159766", "文旅ETF"],
    "biotech": ["创新药ETF", "159992", "生物医药ETF"],
    "consumer": ["消费ETF", "159928", "大消费ETF"],
    "semiconductor": ["芯片ETF", "159995", "半导体ETF"],
    "electronics": ["电子ETF", "159997", "电子板块"],
    "ai_computing": ["AI算力ETF", "算力ETF", "人工智能ETF"],
    "cpo": ["通信ETF", "515880", "光模块"],
    "computer": ["计算机ETF", "512720", "计算机板块"],
    "communication": ["5G通信ETF", "515050", "通信板块"],
    "military": ["军工ETF", "军工板块", "航空航天"],
    "robot": ["机器人ETF", "人形机器人", "减速器"],
    "media": ["传媒ETF", "512980", "传媒板块"],
    "coal": ["煤炭ETF", "515220", "煤炭板块"],
    "crude_oil": ["原油ETF", "501018", "原油基金"],
    "newenergy": ["新能源ETF", "516160", "光伏ETF"],
    "battery": ["电池ETF", "159755", "锂电池ETF"],
    "power_grid": ["电网ETF", "159611", "电力设备ETF"],
    "infrastructure": ["基建ETF", "516950", "基建板块"],
    "nonferrous": ["有色ETF", "512400", "有色金属"],
    "chemical": ["化工ETF", "516220", "化工板块"],
    "steel": ["钢铁ETF", "515210", "钢铁板块"],
    "realestate": ["房地产ETF", "512200", "地产板块"],
    "nasdaq": ["纳指ETF", "纳斯达克ETF", "美股ETF"],
    "gold": ["黄金ETF", "518880", "黄金投资"],
}


def _empty_result() -> Dict[str, List[Dict]]:
    return {s: [] for s in ALL_SECTORS}


def collect_all() -> Dict[str, List[Dict]]:
    """雪球2025年底加强WAF，/statuses/search.json返回400016需登录，无登录态降级返回空数据。"""
    result = _empty_result()
    print("  [雪球社区] ⚠️ 雪球讨论 API 需登录账号（400016 WAF），本采集器降级跳过")
    print("  [雪球社区] 提示：东方财富股吧已覆盖板块新闻数据，可作为替代信号源")
    return result


if __name__ == "__main__":  # pragma: no cover
    data = collect_all()
    for key, value in data.items():
        print(f"{key}: {len(value)} posts")
