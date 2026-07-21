"""宝妈指数计算引擎，各板块独立计算并维护历史曲线。"""
from datetime import datetime, date
from typing import Dict, List
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

SECTOR_NAMES = {
    "bank": "银行",
    "securities": "券商",
    "insurance": "保险",
    "baijiu": "白酒",
    "food": "食品",
    "medicine": "医药",
    "appliance": "家电",
    "tourism": "文旅",
    "biotech": "创新药",
    "consumer": "消费",
    "electronics": "电子",
    "computer": "计算机",
    "communication": "通信",
    "media": "传媒",
    "cpo": "CPO通信",
    "semiconductor": "半导体",
    "nonferrous": "有色",
    "coal": "煤炭",
    "chemical": "化工",
    "steel": "钢铁",
    "realestate": "地产",
    "infrastructure": "基建",
    "newenergy": "新能源",
    "nasdaq": "纳斯达克",
    "gold": "黄金"
}


def _empty_details() -> Dict:
    return {
        "total_posts": 0,
        "valid_posts": 0,
        "spam_posts": 0,
        "newbie_posts": 0,
        "pure_newbie": 0,
        "newbie_ratio": 0.0,
        "avg_newbie_score": 0.0,
        "avg_sentiment": 0.0,
        "purity_signal": 0.0,
        "activity": 0.0,
        "mom_buy_index": 0.0,
        "mom_sell_index": 0.0,
        "buy_sell_ratio": 0.0,
        "buy_count": 0,
        "sell_count": 0,
    }


def compute_sector_index(analysis_results: List) -> Dict:
    """计算单个板块的宝妈指数(0-100)，四个维度加权计算。"""
    if not analysis_results:
        return {
            "index": 0,
            "interpretation": "无数据",
            "details": _empty_details(),
            "top_newbie_posts": [],
        }
    
    total = len(analysis_results)
    
    valid_posts = [r for r in analysis_results if r.level != "垃圾帖"]
    spam_count = total - len(valid_posts)
    
    newbie_posts = [r for r in analysis_results if r.newbie_score >= 20]
    pure_newbie = [r for r in analysis_results if r.newbie_score >= 50]
    newbie_count = len(newbie_posts)
    
    newbie_ratio = (newbie_count / len(valid_posts)) * 100 if valid_posts else 0
    
    avg_newbie_score = sum(r.newbie_score for r in newbie_posts) / max(newbie_count, 1)
    
    sentiments = [abs(r.sentiment_score) for r in newbie_posts]
    avg_sentiment = sum(sentiments) / max(len(sentiments), 1) * 100
    
    purity_signal = (len(pure_newbie) / max(newbie_count, 1)) * 100 if newbie_count > 0 else 0
    activity_signal = min(100, len(valid_posts) / 80 * 100)
    
    index = (
        newbie_ratio * 0.40 +
        avg_newbie_score * 0.25 +
        avg_sentiment * 0.20 +
        purity_signal * 0.15
    )
    
    index = round(min(100, index), 1)
    
    newbie_buy = [r for r in newbie_posts if r.intent == "buy"]
    newbie_sell = [r for r in newbie_posts if r.intent == "sell"]
    
    buy_ratio = len(newbie_buy) / max(newbie_count, 1)
    sell_ratio = len(newbie_sell) / max(newbie_count, 1)
    buy_intensity = sum(r.intent_strength for r in newbie_buy) / max(len(newbie_buy), 1)
    sell_intensity = sum(r.intent_strength for r in newbie_sell) / max(len(newbie_sell), 1)
    
    mom_buy_index = round(min(100, (
        buy_ratio * 100 * 0.50 +
        (avg_newbie_score / 100) * buy_ratio * 30 * 0.30 +
        buy_intensity * 100 * 0.20
    )), 1)
    
    mom_sell_index = round(min(100, (
        sell_ratio * 100 * 0.50 +
        (avg_newbie_score / 100) * sell_ratio * 30 * 0.30 +
        sell_intensity * 100 * 0.20
    )), 1)
    
    buy_sell_ratio = round(min(20, len(newbie_buy) / max(len(newbie_sell), 1)), 1)
    
    return {
        "index": index,
        "interpretation": interpret_index(index),
        "details": {
            "total_posts": total,
            "valid_posts": len(valid_posts),
            "spam_posts": spam_count,
            "newbie_posts": newbie_count,
            "pure_newbie": len(pure_newbie),
            "newbie_ratio": round(newbie_ratio, 1),
            "avg_newbie_score": round(avg_newbie_score, 1),
            "avg_sentiment": round(avg_sentiment, 1),
            "purity_signal": round(purity_signal, 1),
            "activity": round(activity_signal, 1),
            "mom_buy_index": mom_buy_index,
            "mom_sell_index": mom_sell_index,
            "buy_sell_ratio": buy_sell_ratio,
            "buy_count": len(newbie_buy),
            "sell_count": len(newbie_sell),
        },
        "top_newbie_posts": [
            {
                "title": r.title[:60],
                "score": r.newbie_score,
                "level": r.level,
                "reasoning": r.reasoning[:150],
                "sentiment": r.sentiment_score,
                "intent": r.intent,
                "intent_label": {"buy": "🟢 买入", "sell": "🔴 卖出", "neutral": "⚪ 观望"}.get(r.intent, ""),
                "key_signals": r.key_signals[:2],
            }
            for r in sorted(newbie_posts, key=lambda x: x.newbie_score, reverse=True)[:5]
        ],
    }


def interpret_index(index: float) -> str:
    if index >= 75:
        return "🔴 极度狂热 — 擦鞋童时刻！小白情绪爆表，历史级别的危险信号"
    elif index >= 60:
        return "🟠 高度警惕 — 小白大量涌入，市场情绪过热，建议大幅减仓"
    elif index >= 40:
        return "🟡 开始升温 — 小白活跃度明显上升，需保持关注"
    elif index >= 20:
        return "🟢 正常区间 — 小白参与度适中，无需特别操作"
    else:
        return "🔵 极度冷清 — 小白沉默不语，可能是市场底部信号"


def load_history() -> Dict:
    history_file = os.path.join(DATA_DIR, "history.json")
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = data.get("records", [])
        if len(records) > 0:
            seen = {}
            invalid_count = 0
            for record in records:
                date = record.get("date")
                if not date:
                    invalid_count += 1
                    continue
                if date in seen:
                    old_ts = seen[date].get("timestamp", "")
                    new_ts = record.get("timestamp", "")
                    if new_ts >= old_ts:
                        seen[date] = record
                else:
                    seen[date] = record
            deduped = sorted(seen.values(), key=lambda r: r["date"])
            changed = False
            if len(deduped) != len(records) - invalid_count:
                print(f"  [历史数据] 日期去重: {len(records)} → {len(deduped)} 条")
                changed = True
            if invalid_count > 0:
                print(f"  [历史数据] 跳过无 date 字段的记录: {invalid_count} 条")
                changed = True
            if changed:
                data["records"] = deduped
        return data
    return {"records": []}


def save_history(history: Dict):
    history_file = os.path.join(DATA_DIR, "history.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = history_file + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, history_file)


def add_record(sector_indices: Dict[str, Dict], analysis_results: Dict):
    history = load_history()
    
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "sectors": sector_indices,
    }
    
    today = record["date"]
    existing = [r for r in history["records"] if r["date"] == today]
    if existing:
        history["records"] = [r for r in history["records"] if r["date"] != today]
    
    history["records"].append(record)
    history["records"].sort(key=lambda r: r["date"])
    save_history(history)


def _empty_sector_data() -> Dict:
    return {
        "index": 0,
        "interpretation": "无数据",
        "details": _empty_details(),
        "top_newbie_posts": [],
    }


def get_dashboard_data() -> Dict:
    history = load_history()
    records = history.get("records", [])

    latest = records[-1] if records else None

    sector_history = {code: [] for code in SECTOR_NAMES}

    for r in records:
        for sector, data in r.get("sectors", {}).items():
            if sector in sector_history:
                sector_history[sector].append({
                    "date": r["date"],
                    "index": data["index"],
                })

    if latest:
        sectors = latest.get("sectors", {})
        for sector in sector_history.keys():
            if sector not in sectors:
                sectors[sector] = _empty_sector_data()

    return {
        "latest": latest,
        "sector_history": sector_history,
        "record_count": len(records),
    }
