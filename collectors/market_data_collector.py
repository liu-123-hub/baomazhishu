"""行情数据采集器，基于 AKShare（新浪财经数据源）获取 ETF 和指数日线。"""
import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import akshare

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from analyzer.index_calculator import SECTOR_NAMES, SECTOR_META, get_sector_type

DATA_DIR = os.path.join(PROJECT_ROOT, "data")
MARKET_DATA_FILE = os.path.join(DATA_DIR, "market_data.json")

SECTOR_ETF_MAP = {
    # ── T1：AI算力硬科技 ──
    "semiconductor":     {"code": "159995", "name": "芯片ETF",       "ak_symbol": "sz159995"},
    "electronics":       {"code": "159997", "name": "电子ETF",       "ak_symbol": "sz159997"},
    "ai_computing":      {"code": "159819", "name": "人工智能ETF",    "ak_symbol": "sz159819"},
    "cpo":               {"code": "515880", "name": "通信ETF",       "ak_symbol": "sh515880"},
    "ai_application":    {"code": "159819", "name": "人工智能ETF(AI应用)", "ak_symbol": "sz159819"},  # 人工智能ETF（覆盖AI应用落地）
    "deepseek":          {"code": "588730", "name": "科创人工智能ETF","ak_symbol": "sh588730"},  # 科创板AI ETF（DeepSeek概念）
    # ── T2：高端制造/智能科技 ──
    "computer":          {"code": "512720", "name": "计算机ETF",     "ak_symbol": "sh512720"},
    "communication":     {"code": "515050", "name": "5G通信ETF",     "ak_symbol": "sh515050"},
    "military":          {"code": "512660", "name": "军工ETF",       "ak_symbol": "sh512660"},
    "robot":             {"code": "562500", "name": "机器人ETF",     "ak_symbol": "sh562500"},
    "humanoid_robot":    {"code": "159770", "name": "机器人ETF天弘", "ak_symbol": "sz159770"},  # 覆盖人形机器人产业链
    "ai_agent":          {"code": "516510", "name": "云计算ETF",     "ak_symbol": "sh516510"},  # AI Agent运行基础设施
    "low_altitude":      {"code": "159378", "name": "通用航空ETF",   "ak_symbol": "sz159378"},  # 全市场首只低空经济ETF
    "satellite_internet":{"code": "159206", "name": "卫星ETF",       "ak_symbol": "sz159206"},
    # ── T3：新能源/电力设备 ──
    "newenergy":         {"code": "516160", "name": "新能源ETF",     "ak_symbol": "sh516160"},
    "battery":           {"code": "159755", "name": "电池ETF",       "ak_symbol": "sz159755"},
    "power_grid":        {"code": "159611", "name": "电网ETF",       "ak_symbol": "sz159611"},
    "solid_battery":     {"code": "159755", "name": "电池ETF(固态电池)", "ak_symbol": "sz159755"},  # 持仓覆盖固态电池产业链
    "nuclear_fusion":    {"code": "561790", "name": "央企现代能源ETF","ak_symbol": "sh561790"},  # 最接近核聚变主题
    # ── T4：消费医疗/文化传媒 ──
    "medicine":          {"code": "512010", "name": "医药ETF",      "ak_symbol": "sh512010"},
    "baijiu":            {"code": "512690", "name": "酒ETF",        "ak_symbol": "sh512690"},
    "food":              {"code": "515080", "name": "食品ETF",      "ak_symbol": "sh515080"},
    "appliance":         {"code": "159996", "name": "家电ETF",      "ak_symbol": "sz159996"},
    "tourism":           {"code": "159766", "name": "旅游ETF",      "ak_symbol": "sz159766"},
    "media":             {"code": "512980", "name": "传媒ETF",      "ak_symbol": "sh512980"},
    "biotech":           {"code": "159992", "name": "创新药ETF",    "ak_symbol": "sz159992"},
    "consumer":          {"code": "159928", "name": "消费ETF",      "ak_symbol": "sz159928"},
    # ── V1：大金融 ──
    "bank":              {"code": "512800", "name": "银行ETF",      "ak_symbol": "sh512800"},
    "securities":        {"code": "512880", "name": "证券ETF",      "ak_symbol": "sh512880"},
    "insurance":         {"code": "512570", "name": "保险ETF",      "ak_symbol": "sh512570"},
    # ── V2：周期资源 ──
    "coal":              {"code": "515220", "name": "煤炭ETF",      "ak_symbol": "sh515220"},
    "crude_oil":         {"code": "501018", "name": "原油基金",     "ak_symbol": "sh501018"},
    "nonferrous":        {"code": "512400", "name": "有色ETF",      "ak_symbol": "sh512400"},
    "chemical":          {"code": "516220", "name": "化工ETF",      "ak_symbol": "sh516220"},
    "steel":             {"code": "515210", "name": "钢铁ETF",      "ak_symbol": "sh515210"},
    # ── V3：基建地产 ──
    "infrastructure":    {"code": "516950", "name": "基建ETF",      "ak_symbol": "sh516950"},
    "realestate":        {"code": "512200", "name": "房地产ETF",    "ak_symbol": "sh512200"},
    # ── DEF：防御资产/海外 ──
    "gold":              {"code": "518880", "name": "黄金ETF",      "ak_symbol": "sh518880"},
    "nasdaq":            {"code": "513100", "name": "纳指ETF",      "ak_symbol": "sh513100"},
}

BENCHMARK_INDICES = {
    "sh000001": "上证指数",
    "sh000300": "沪深300",
    "sz399006": "创业板指",
}

REQUEST_INTERVAL = 0.5
MAX_RETRIES = 2


def load_market_data() -> Dict:
    if os.path.exists(MARKET_DATA_FILE):
        with open(MARKET_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "etf_data": {},
        "benchmark_indices": {},
        "last_update": None,
        "update_count": 0,
    }


def save_market_data(data: Dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = MARKET_DATA_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, MARKET_DATA_FILE)


def _fetch_etf_daily(ak_symbol: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            df = akshare.fund_etf_hist_sina(symbol=ak_symbol)
            if df is None or df.empty:
                print(f"    [{ak_symbol}] 无数据返回")
                return None

            records = []
            prev_close = None
            for _, row in df.iterrows():
                date_str = str(row.get("date", ""))
                if date_str < start_date or date_str > end_date:
                    prev_close = float(row.get("close", 0))
                    continue

                close_val = round(float(row.get("close", 0)), 4)
                change_pct = None
                if prev_close is not None and prev_close != 0:
                    change_pct = round((close_val - prev_close) / prev_close * 100, 2)

                records.append({
                    "date": date_str,
                    "open": round(float(row.get("open", 0)), 4),
                    "high": round(float(row.get("high", 0)), 4),
                    "low": round(float(row.get("low", 0)), 4),
                    "close": close_val,
                    "volume": int(row.get("volume", 0)),
                    "amount": round(float(row.get("amount", 0)), 2),
                    "change_pct": change_pct,
                })
                prev_close = close_val

            return records

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                print(f"    [{ak_symbol}] 获取失败: {e}")
                return None

    return None


def collect_etf_data(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    result = {}
    print("  [行情数据] 开始采集 ETF 日线行情 (新浪财经数据源)...")

    for sector, etf_info in SECTOR_ETF_MAP.items():
        ak_symbol = etf_info["ak_symbol"]
        print(f"    [{etf_info['name']}({etf_info['code']})] 获取中...")
        records = _fetch_etf_daily(ak_symbol, start_date, end_date)
        if records:
            result[sector] = records
            print(f"    [{etf_info['name']}] 获取到 {len(records)} 条日线数据")
        else:
            print(f"    [{etf_info['name']}] 获取失败，跳过")
        time.sleep(REQUEST_INTERVAL)

    return result


def _fetch_index_daily(index_code: str, start_date: str, end_date: str) -> Optional[List[Dict]]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            df = akshare.stock_zh_index_daily(symbol=index_code)
            if df is None or df.empty:
                print(f"    [{index_code}] 无数据返回")
                return None

            records = []
            prev_close = None
            for _, row in df.iterrows():
                date_str = str(row.get("date", ""))
                if date_str < start_date or date_str > end_date:
                    prev_close = float(row.get("close", 0))
                    continue

                close_val = round(float(row.get("close", 0)), 2)
                change_pct = None
                if prev_close is not None and prev_close != 0:
                    change_pct = round((close_val - prev_close) / prev_close * 100, 2)

                records.append({
                    "date": date_str,
                    "open": round(float(row.get("open", 0)), 2),
                    "high": round(float(row.get("high", 0)), 2),
                    "low": round(float(row.get("low", 0)), 2),
                    "close": close_val,
                    "volume": int(row.get("volume", 0)),
                    "change_pct": change_pct,
                })
                prev_close = close_val

            return records

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                print(f"    [{index_code}] 获取失败: {e}")
                return None

    return None


def collect_benchmark_indices(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    result = {}
    print("  [行情数据] 开始采集市场基准指数...")

    for index_code, index_name in BENCHMARK_INDICES.items():
        print(f"    [{index_name}({index_code})] 获取中...")
        records = _fetch_index_daily(index_code, start_date, end_date)
        if records:
            result[index_code] = {"name": index_name, "data": records}
            print(f"    [{index_name}] 获取到 {len(records)} 条日线数据")
        else:
            print(f"    [{index_name}] 获取失败，跳过")
        time.sleep(REQUEST_INTERVAL)

    return result


def _should_update(existing: Dict) -> bool:
    last = existing.get("last_update")
    if not last:
        return True
    today = datetime.now().strftime("%Y%m%d")
    return last < today


def collect_all(start_date: Optional[str] = None, end_date: Optional[str] = None, force: bool = False) -> Dict:
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    existing = load_market_data()

    if not force and not _should_update(existing):
        print("  [行情数据] 今日已更新，跳过（force=True 可强制更新）")
        return existing

    new_etf = collect_etf_data(start_date, end_date)
    new_idx = collect_benchmark_indices(start_date, end_date)

    existing_etf = existing.get("etf_data", {})
    for sector, records in new_etf.items():
        existing_etf.setdefault(sector, [])
        existing_dates = {r["date"] for r in existing_etf[sector]}
        for rec in records:
            if rec["date"] not in existing_dates:
                existing_etf[sector].append(rec)
                existing_dates.add(rec["date"])
        existing_etf[sector].sort(key=lambda x: x["date"])

    existing_idx = existing.get("benchmark_indices", {})
    for code, idx_data in new_idx.items():
        if code not in existing_idx:
            existing_idx[code] = idx_data
        else:
            existing_dates = {r["date"] for r in existing_idx[code].get("data", [])}
            for rec in idx_data.get("data", []):
                if rec["date"] not in existing_dates:
                    existing_idx[code]["data"].append(rec)
                    existing_dates.add(rec["date"])
            existing_idx[code]["data"].sort(key=lambda x: x["date"])

    existing["etf_data"] = existing_etf
    existing["benchmark_indices"] = existing_idx
    existing["last_update"] = datetime.now().strftime("%Y%m%d")
    existing["update_count"] = existing.get("update_count", 0) + 1

    save_market_data(existing)
    total_etf_records = sum(len(v) for v in existing_etf.values())
    print(f"  [行情数据] 已保存至 {MARKET_DATA_FILE}")
    print(f"  [行情数据] ETF 板块: {len(existing_etf)} 个，总记录: {total_etf_records} 条")
    print(f"  [行情数据] 基准指数: {len(existing_idx)} 个，更新次数: {existing['update_count']}")

    return existing


def validate_market_data(data: Dict) -> Dict:
    issues = []
    stats = {"total_sectors": 0, "total_records": 0, "valid_sectors": 0, "issues": 0}

    etf_data = data.get("etf_data", {})
    for sector, records in etf_data.items():
        stats["total_sectors"] += 1
        if not records:
            issues.append(f"[{sector}] 无行情数据")
            continue

        stats["total_records"] += len(records)
        ok = True

        for i, r in enumerate(records):
            o, h, l, c = r.get("open"), r.get("high"), r.get("low"), r.get("close")
            if None in (o, h, l, c):
                issues.append(f"[{sector}] {r['date']}: 缺少 OHLC")
                ok = False; continue
            if h < l:
                issues.append(f"[{sector}] {r['date']}: high({h}) < low({l})")
                ok = False
            if h < max(o, c):
                issues.append(f"[{sector}] {r['date']}: high({h}) < max(open,close)")
                ok = False
            if l > min(o, c):
                issues.append(f"[{sector}] {r['date']}: low({l}) > min(open,close)")
                ok = False

            if i > 0:
                prev = records[i - 1]["close"]
                if prev and prev != 0:
                    exp = round((c - prev) / prev * 100, 2)
                    act = r.get("change_pct")
                    if act is not None and abs(exp - act) > 2:
                        issues.append(f"[{sector}] {r['date']}: 涨跌幅偏差 预期{exp}% 实际{act}%")

        if ok:
            stats["valid_sectors"] += 1

    stats["issues"] = len(issues)
    return {"stats": stats, "issues": issues}


if __name__ == "__main__":  # pragma: no cover
    print("=" * 50)
    print("  行情数据采集器测试 (新浪财经数据源)")
    print("=" * 50)
    data = collect_all()
    print("\n数据质量校验:")
    v = validate_market_data(data)
    print(f"  板块数: {v['stats']['total_sectors']}")
    print(f"  有效板块: {v['stats']['valid_sectors']}")
    print(f"  总记录: {v['stats']['total_records']}")
    print(f"  问题数: {v['stats']['issues']}")
    if v["issues"]:
        for issue in v["issues"][:10]:
            print(f"    - {issue}")
