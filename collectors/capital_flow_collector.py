"""市场异动数据采集器，基于 AKShare 获取涨停池和龙虎榜数据。"""
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import akshare

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CAPITAL_FLOW_FILE = os.path.join(DATA_DIR, "capital_flow.json")

REQUEST_INTERVAL = 0.5
MAX_RETRIES = 2
DEFAULT_LOOKBACK_DAYS = 30


def load_capital_flow() -> Dict:
    """加载已有的市场异动数据文件。"""
    if os.path.exists(CAPITAL_FLOW_FILE):
        with open(CAPITAL_FLOW_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "limit_up_pool": {"data": [], "last_update": None},
        "dragon_tiger_list": {"data": [], "last_update": None},
        "last_update": None,
        "update_count": 0,
    }


def save_capital_flow(data: Dict):
    """原子写入市场异动数据文件。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = CAPITAL_FLOW_FILE + ".tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, CAPITAL_FLOW_FILE)


def _fetch_limit_up_pool(trade_date: str) -> Optional[List[Dict]]:
    """通过 AKShare 获取指定交易日涨停池数据。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            df = akshare.stock_zt_pool_em(date=trade_date)
            if df is None or df.empty:
                return None

            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("代码", "")).strip(),
                    "name": str(row.get("名称", "")).strip(),
                    "change_pct": _to_float(row.get("涨跌幅")),
                    "close": _to_float(row.get("最新价")),
                    "amount": _to_float(row.get("成交额")),
                    "circulating_mv": _to_float(row.get("流通市值")),
                    "total_mv": _to_float(row.get("总市值")),
                    "turnover": _to_float(row.get("换手率")),
                    "first_time": str(row.get("首次封板时间", "")).strip(),
                    "last_time": str(row.get("最后封板时间", "")).strip(),
                    "break_count": _to_int(row.get("炸板次数")),
                    "limit_up_days": _to_int(row.get("连板数")),
                    "industry": str(row.get("所属行业", "")).strip(),
                })

            return records

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                print(f"    [涨停池] {trade_date} 获取失败: {e}")
                return None

    return None


def collect_limit_up_pool(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    """采集最近 N 天的涨停池数据，按交易日聚合。"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
    trade_dates = _generate_trade_dates(end_date, max(days, 1))

    result = {}
    print(f"  [涨停池] 开始采集 {start_date} ~ {end_date} 数据...")
    for date_str in trade_dates:
        records = _fetch_limit_up_pool(date_str)
        if records:
            result[date_str] = records
            print(f"    [{date_str}] 采集到 {len(records)} 条")
        time.sleep(REQUEST_INTERVAL)

    return result


def _fetch_dragon_tiger_list(trade_date: str) -> Optional[List[Dict]]:
    """通过 AKShare 获取指定交易日龙虎榜数据。"""
    for attempt in range(MAX_RETRIES + 1):
        try:
            df = akshare.stock_lhb_detail_daily_sina(date=trade_date)
            if df is None or df.empty:
                return None

            records = []
            for _, row in df.iterrows():
                records.append({
                    "code": str(row.get("股票代码", "")).strip(),
                    "name": str(row.get("股票名称", "")).strip(),
                    "close": _to_float(row.get("收盘价")),
                    "change_pct": _to_float(row.get("对应值")),
                    "volume": _to_float(row.get("成交量")),
                    "amount": _to_float(row.get("成交额")),
                    "indicator": str(row.get("指标", "")).strip(),
                })

            return records

        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(2)
            else:
                print(f"    [龙虎榜] {trade_date} 获取失败: {e}")
                return None

    return None


def collect_dragon_tiger_list(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    """采集最近 N 天的龙虎榜数据，按交易日聚合。"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days + 1
    trade_dates = _generate_trade_dates(end_date, max(days, 1))

    result = {}
    print(f"  [龙虎榜] 开始采集 {start_date} ~ {end_date} 数据...")
    for date_str in trade_dates:
        records = _fetch_dragon_tiger_list(date_str)
        if records:
            result[date_str] = records
            print(f"    [{date_str}] 采集到 {len(records)} 条")
        time.sleep(REQUEST_INTERVAL)

    return result


def _generate_trade_dates(end_date: str, days: int) -> List[str]:
    """生成最近 N 个自然日对应的交易日字符串（YYYYMMDD）。"""
    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
    return [(end_dt - timedelta(days=i)).strftime("%Y%m%d") for i in range(days)]


def _to_float(value) -> Optional[float]:
    """安全转换为浮点数，失败返回 None。"""
    if value is None:
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _to_int(value) -> Optional[int]:
    """安全转换为整数，失败返回 None。"""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _should_update(existing: Dict) -> bool:
    """判断是否需要更新：今天尚未更新或从未更新。"""
    last = existing.get("last_update")
    if not last:
        return True
    today = datetime.now().strftime("%Y%m%d")
    return last < today


def collect_all(start_date: Optional[str] = None, end_date: Optional[str] = None, force: bool = False) -> Dict:
    """采集所有市场异动数据，支持增量更新（按日期去重合并）。"""
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%d")

    existing = load_capital_flow()

    if not force and not _should_update(existing):
        print("  [市场异动] 今日已更新，跳过（force=True 可强制更新）")
        return existing

    new_limit_up = collect_limit_up_pool(start_date, end_date)
    new_dtl = collect_dragon_tiger_list(start_date, end_date)

    existing_lu = existing.get("limit_up_pool", {})
    existing_lu_data = existing_lu.get("data", [])
    existing_lu_dates = {d["date"] for d in existing_lu_data}
    for date_str, stocks in new_limit_up.items():
        iso_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        if iso_date not in existing_lu_dates:
            existing_lu_data.append({"date": iso_date, "stocks": stocks})
            existing_lu_dates.add(iso_date)
    existing_lu_data.sort(key=lambda x: x["date"])
    existing_lu["data"] = existing_lu_data
    existing_lu["last_update"] = datetime.now().isoformat()

    existing_dtl = existing.get("dragon_tiger_list", {})
    existing_dtl_data = existing_dtl.get("data", [])
    existing_dtl_dates = {d["date"] for d in existing_dtl_data}
    for date_str, stocks in new_dtl.items():
        iso_date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
        if iso_date not in existing_dtl_dates:
            existing_dtl_data.append({"date": iso_date, "stocks": stocks})
            existing_dtl_dates.add(iso_date)
    existing_dtl_data.sort(key=lambda x: x["date"])
    existing_dtl["data"] = existing_dtl_data
    existing_dtl["last_update"] = datetime.now().isoformat()

    existing["limit_up_pool"] = existing_lu
    existing["dragon_tiger_list"] = existing_dtl
    existing["last_update"] = datetime.now().strftime("%Y%m%d")
    existing["update_count"] = existing.get("update_count", 0) + 1

    save_capital_flow(existing)
    print(f"  [市场异动] 已保存至 {CAPITAL_FLOW_FILE}")
    print(f"  [市场异动] 涨停池交易日: {len(existing_lu_data)} 天")
    print(f"  [市场异动] 龙虎榜交易日: {len(existing_dtl_data)} 天")

    return existing


def validate_capital_flow(data: Dict) -> Dict:
    """校验市场异动数据完整性：必填字段、数值合法性、日期升序。"""
    issues = []
    stats = {
        "limit_up_days": 0,
        "limit_up_total_stocks": 0,
        "limit_up_valid_days": 0,
        "dtl_trade_days": 0,
        "dtl_total_stocks": 0,
        "dtl_valid_days": 0,
        "issues": 0,
    }

    lu_data = data.get("limit_up_pool", {}).get("data", [])
    stats["limit_up_days"] = len(lu_data)

    prev_date = None
    for day in lu_data:
        date_str = day.get("date")
        stocks = day.get("stocks", [])
        stats["limit_up_total_stocks"] += len(stocks)
        day_ok = True
        if not date_str:
            issues.append("[涨停池] 存在缺少日期的记录")
            day_ok = False
        if prev_date and date_str and date_str <= prev_date:
            issues.append(f"[涨停池] 日期非升序: {prev_date} -> {date_str}")
            day_ok = False
        prev_date = date_str

        for s in stocks:
            for field in ("code", "name", "close", "change_pct"):
                if s.get(field) is None:
                    issues.append(f"[涨停池] {date_str}/{s.get('code')}: 缺少字段 {field}")
                    day_ok = False
            if s.get("close") is not None and s["close"] <= 0:
                issues.append(f"[涨停池] {date_str}/{s.get('code')}: 收盘价异常({s.get('close')})")
                day_ok = False
            if s.get("change_pct") is not None and not (0 <= s["change_pct"] <= 30):
                issues.append(f"[涨停池] {date_str}/{s.get('code')}: 涨跌幅异常({s.get('change_pct')})")
                day_ok = False

        if day_ok:
            stats["limit_up_valid_days"] += 1

    dtl_data = data.get("dragon_tiger_list", {}).get("data", [])
    stats["dtl_trade_days"] = len(dtl_data)

    prev_date = None
    for day in dtl_data:
        date_str = day.get("date")
        stocks = day.get("stocks", [])
        stats["dtl_total_stocks"] += len(stocks)
        day_ok = True
        if not date_str:
            issues.append("[龙虎榜] 存在缺少日期的记录")
            day_ok = False
        if prev_date and date_str and date_str <= prev_date:
            issues.append(f"[龙虎榜] 日期非升序: {prev_date} -> {date_str}")
            day_ok = False
        prev_date = date_str

        for s in stocks:
            for field in ("code", "name", "close", "change_pct"):
                if s.get(field) is None:
                    issues.append(f"[龙虎榜] {date_str}/{s.get('code')}: 缺少字段 {field}")
                    day_ok = False
            if s.get("close") is not None and s["close"] <= 0:
                issues.append(f"[龙虎榜] {date_str}/{s.get('code')}: 收盘价异常({s.get('close')})")
                day_ok = False

        if day_ok:
            stats["dtl_valid_days"] += 1

    stats["issues"] = len(issues)
    return {"stats": stats, "issues": issues}


if __name__ == "__main__":  # pragma: no cover
    print("=" * 50)
    print("  市场异动数据采集器测试 (AKShare)")
    print("=" * 50)
    data = collect_all()
    print("\n数据质量校验:")
    v = validate_capital_flow(data)
    print(f"  涨停池交易日: {v['stats']['limit_up_days']}")
    print(f"  涨停池个股数: {v['stats']['limit_up_total_stocks']}")
    print(f"  龙虎榜交易日: {v['stats']['dtl_trade_days']}")
    print(f"  龙虎榜个股数: {v['stats']['dtl_total_stocks']}")
    print(f"  问题数: {v['stats']['issues']}")
    if v["issues"]:
        for issue in v["issues"][:10]:
            print(f"    - {issue}")
