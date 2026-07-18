"""数据服务层：大盘数据计算与历史趋势查询。"""
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

from app.database import db
from app.cache import dashboard_cache
from app.config import settings

logger = logging.getLogger(__name__)

JSON_DATA_PATH = str(settings.DATA_DIR / 'dashboard_data.json')
HISTORY_DATA_PATH = str(settings.DATA_DIR / 'history.json')

VALID_SECTORS = set(settings.SECTOR_NAMES.keys())

_PROJECT_ROOT = str(settings.PROJECT_ROOT)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_DATA_FRESHNESS_MAX_HOURS = 24


def _load_from_json_file() -> Dict[str, Any]:
    """从 JSON 文件加载最新数据。"""
    try:
        if not os.path.exists(JSON_DATA_PATH):
            logger.warning(f"JSON 数据文件不存在: {JSON_DATA_PATH}")
            return {}
        with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data or not isinstance(data, dict):
            logger.warning("JSON 数据文件格式异常")
            return {}
        return data.get('latest', {}).get('sectors', {})
    except json.JSONDecodeError as e:
        logger.error(f"JSON 数据文件解析失败: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载 JSON 数据文件异常: {e}")
        return {}


def _load_history_from_json() -> Dict[str, List[Dict]]:
    """从 history.json 加载历史走势数据。"""
    try:
        if not os.path.exists(HISTORY_DATA_PATH):
            logger.warning(f"历史数据文件不存在: {HISTORY_DATA_PATH}")
            return {}
        with open(HISTORY_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data or not isinstance(data, dict):
            logger.warning("历史数据文件格式异常")
            return {}

        records = data.get('records', [])
        if not isinstance(records, list):
            return {}

        result: Dict[str, List[Dict]] = {}
        for record in records:
            if not isinstance(record, dict):
                continue
            date_str = record.get('date')
            if not date_str:
                continue
            sectors = record.get('sectors', {})
            if not isinstance(sectors, dict):
                continue
            for code, sector_data in sectors.items():
                if code not in VALID_SECTORS or not isinstance(sector_data, dict):
                    continue
                value = sector_data.get('index')
                if value is None:
                    value = sector_data.get('index_value')
                if value is None:
                    continue
                try:
                    value_float = float(value)
                except (TypeError, ValueError):
                    continue
                result.setdefault(code, []).append({
                    'date': date_str,
                    'value': value_float
                })

        for code in result:
            seen: Dict[str, Dict] = {}
            for item in result[code]:
                seen[item['date']] = item
            result[code] = sorted(seen.values(), key=lambda x: x['date'])

        return result
    except json.JSONDecodeError as e:
        logger.error(f"历史数据文件解析失败: {e}")
        return {}
    except Exception as e:
        logger.error(f"加载历史数据文件异常: {e}")
        return {}


def _format_update_time(dt: Optional[str]) -> Optional[str]:
    if not dt:
        return None
    return dt


def _load_data_provenance() -> Dict[str, Any]:
    """加载数据溯源信息。"""
    try:
        if not os.path.exists(JSON_DATA_PATH):
            return {'available': False, 'reason': '数据文件尚未生成（首次启动或采集未完成）'}
        with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {'available': False, 'reason': '数据文件格式异常'}
        provenance = data.get('data_provenance')
        if not provenance:
            return {'available': False, 'reason': '数据文件中未包含溯源信息（旧版本数据）'}
        return {'available': True, **provenance}
    except Exception as e:
        logger.error(f"加载数据溯源信息失败: {e}")
        return {'available': False, 'reason': f'加载异常: {str(e)}'}


def _compute_trend(history: List[Dict]) -> str:
    """根据最近两条历史记录计算趋势。"""
    if not history or len(history) < 2:
        return '平稳'
    try:
        def _extract_value(item):
            v = item.get('index_value')
            if v is None:
                v = item.get('value')
            return float(v) if v is not None else None

        current = _extract_value(history[-1])
        previous = _extract_value(history[-2])
        if current is None or previous is None:
            return '平稳'
        if current > previous * 1.02:
            return '上涨'
        if current < previous * 0.98:
            return '下跌'
    except (TypeError, ValueError):
        pass
    return '平稳'


def _build_merged_history_for_trend(code: str, db_history: List[Dict], json_history_map: Dict[str, List[Dict]]) -> List[Dict]:
    """合并数据库与 history.json 历史数据，同日期以数据库为准。"""
    merged: Dict[str, Dict] = {}
    for item in (json_history_map.get(code) or []):
        date_str = item.get('date')
        if date_str:
            merged[date_str] = {'index_value': item.get('value'), 'record_date': date_str}
    for item in (db_history or []):
        date_str = item.get('record_date')
        if date_str:
            merged[date_str] = item
    return sorted(merged.values(), key=lambda x: x.get('record_date') or '')


def _compute_positive_ratio(row: Dict) -> float:
    """根据买卖指数估算正面情绪比例。"""
    buy = float(row.get('buy_index', 0) or 0)
    sell = float(row.get('sell_index', 0) or 0)
    total = buy + sell
    if total <= 0:
        return 0.0
    return round(buy / total * 100, 1)


def _map_sector_row(row: Dict, history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """将数据库 sector_index 行映射为前端需要的字段格式。"""
    return {
        'code': row.get('sector_code'),
        'index': round(float(row.get('index_value', 0)), 1),
        'post_count': int(row.get('total_posts', 0) or 0),
        'positive_ratio': _compute_positive_ratio(row),
        'trend': _compute_trend(history) if history else '平稳',
        'update_time': _format_update_time(row.get('created_at') or row.get('record_date')),
    }


async def _compute_dashboard_overview() -> Dict[str, Any]:
    """计算大盘概览数据。"""
    try:
        rows = await db.get_latest_sector_index()

        json_history_map = _load_history_from_json()

        sectors = {}
        if rows:
            for row in rows:
                code = row.get('sector_code')
                if not code:
                    continue
                db_history = await db.get_sector_history(code, days=7)
                merged_history = _build_merged_history_for_trend(code, db_history, json_history_map)
                sectors[code] = _map_sector_row(row, merged_history)
        else:
            logger.info("数据库无数据，从 JSON 文件加载")
            json_sectors = _load_from_json_file()
            for code, data in json_sectors.items():
                if not isinstance(data, dict):
                    continue
                details = data.get('details', {})
                merged_history = _build_merged_history_for_trend(code, [], json_history_map)
                sectors[code] = {
                    'code': code,
                    'index': data.get('index', 0),
                    'post_count': details.get('total_posts', 0),
                    'positive_ratio': 0,
                    'trend': _compute_trend(merged_history),
                    'update_time': None,
                }

        sector_count = len(sectors)
        if sector_count == 0:
            avg_index = None
            last_update_time = None
        else:
            total_index = sum(s['index'] for s in sectors.values() if isinstance(s, dict))
            avg_index = round(total_index / sector_count, 1)
            update_times = [s.get('update_time') for s in sectors.values() if isinstance(s, dict) and s.get('update_time')]
            last_update_time = max(update_times) if update_times else None

        from collectors.data_authenticator import is_data_fresh
        freshness = is_data_fresh(last_update_time, max_age_hours=_DATA_FRESHNESS_MAX_HOURS)

        provenance = _load_data_provenance()

        return {
            'code': 200,
            'data': {
                'avg_index': avg_index,
                'sector_count': sector_count,
                'last_update_time': last_update_time,
                'sectors': sectors,
                'data_freshness': freshness,
                'data_provenance': provenance,
            }
        }
    except Exception as e:
        logger.error(f"计算大盘概览失败: {e}")
        return {
            'code': 500,
            'message': f'数据计算异常: {str(e)}',
            'data': None
        }


async def get_dashboard_overview() -> Dict[str, Any]:
    """获取大盘概览（带缓存）。"""
    return await dashboard_cache.get_or_set('dashboard_overview', _compute_dashboard_overview, ttl=30)


async def _compute_sector_detail(code: str) -> Dict[str, Any]:
    """计算板块详情。"""
    try:
        rows = await db.get_latest_sector_index(code)
        json_history_map = _load_history_from_json()
        if rows:
            row = rows[0]
            db_history = await db.get_sector_history(code, days=7)
            merged_history = _build_merged_history_for_trend(code, db_history, json_history_map)
            return {
                'code': 200,
                'data': _map_sector_row(row, merged_history)
            }

        sectors = _load_from_json_file()
        if code in sectors and isinstance(sectors[code], dict):
            sector_data = sectors[code]
            details = sector_data.get('details', {})
            merged_history = _build_merged_history_for_trend(code, [], json_history_map)
            return {
                'code': 200,
                'data': {
                    'code': code,
                    'index': sector_data.get('index', 0),
                    'post_count': details.get('total_posts', 0),
                    'positive_ratio': 0,
                    'trend': _compute_trend(merged_history),
                    'update_time': None,
                }
            }
        return {
            'code': 200,
            'message': '板块不存在',
            'data': None
        }
    except Exception as e:
        logger.error(f"计算板块详情失败 [{code}]: {e}")
        return {
            'code': 500,
            'message': f'数据查询异常: {str(e)}',
            'data': None
        }


async def get_sector_detail(code: str) -> Dict[str, Any]:
    """获取板块详情（带缓存）。"""
    return await dashboard_cache.get_or_set(f'sector_detail_{code}', lambda: _compute_sector_detail(code), ttl=60)


async def _compute_history_trend(code: Optional[str], days: int = 7) -> Dict[str, Any]:
    """计算历史趋势，合并数据库与 history.json 数据。"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        json_history = _load_history_from_json()

        db_history: Dict[str, List[Dict]] = {}
        if code:
            rows = await db.get_sector_history(code, days=days)
            if rows:
                db_history[code] = [
                    {'date': r.get('record_date'), 'value': r.get('index_value')}
                    for r in rows
                    if r.get('record_date') is not None
                ]
        else:
            result = await db.get_all_sectors_history(days=days)
            if result:
                for c, rows in result.items():
                    db_history[c] = [
                        {'date': r.get('record_date'), 'value': r.get('index_value')}
                        for r in rows
                        if r.get('record_date') is not None
                    ]

        merged: Dict[str, Dict[str, Dict]] = {}
        for c, items in json_history.items():
            if code and c != code:
                continue
            for item in items:
                date_str = item.get('date')
                if not date_str:
                    continue
                merged.setdefault(c, {})[date_str] = item
        for c, items in db_history.items():
            if code and c != code:
                continue
            for item in items:
                date_str = item.get('date')
                if not date_str:
                    continue
                merged.setdefault(c, {})[date_str] = item

        formatted: Dict[str, List[Dict]] = {}
        for c, date_map in merged.items():
            sorted_items = sorted(date_map.values(), key=lambda x: x['date'])
            filtered = [item for item in sorted_items if item['date'] >= start_date]
            if filtered:
                formatted[c] = filtered

        if not formatted:
            return {'code': 200, 'data': None, 'message': '无历史数据'}

        return {'code': 200, 'data': formatted}
    except Exception as e:
        logger.error(f"计算历史趋势失败 [{code}]: {e}")
        return {'code': 500, 'message': f'数据查询异常: {str(e)}', 'data': None}


async def get_history_trend(code: Optional[str] = None, days: int = 7) -> Dict[str, Any]:
    """获取历史趋势（带缓存）。"""
    return await dashboard_cache.get_or_set(
        f'history_trend_{code}_{days}',
        lambda: _compute_history_trend(code, days),
        ttl=60
    )


async def get_all_sectors_history(days: int = 7) -> Dict[str, Any]:
    """获取所有板块历史数据。"""
    return await get_history_trend(None, days)


async def get_line_chart_data(sectors: str, days: int = 7) -> Dict[str, Any]:
    """获取折线图数据。"""
    sector_list = [s.strip() for s in sectors.split(',') if s.strip()]
    invalid_sectors = [s for s in sector_list if s not in VALID_SECTORS]
    if invalid_sectors:
        logger.warning(f"无效板块参数: {invalid_sectors}")
        return {
            'code': 400,
            'message': f'无效的板块参数: {", ".join(invalid_sectors)}',
            'data': None
        }

    if not sector_list:
        sector_list = sorted(list(VALID_SECTORS))

    try:
        history_data = await get_all_sectors_history(days)
        if not history_data.get('data'):
            return {'code': 200, 'data': None, 'message': '无数据'}

        data = history_data['data']

        all_dates_set = set()
        for code in sector_list:
            if code in data and data[code]:
                for item in data[code]:
                    if item.get('date'):
                        all_dates_set.add(item['date'])
        x_axis = sorted(all_dates_set)

        series_data = []
        legend = []
        for code in sector_list:
            if code in data and data[code]:
                date_value_map = {item['date']: item.get('value') for item in data[code]}
                series_data.append({
                    'name': code,
                    'data': [date_value_map.get(date) for date in x_axis]
                })
                legend.append(code)

        return {
            'code': 200,
            'data': {
                'x_axis': x_axis,
                'legend': legend,
                'series_data': series_data
            }
        }
    except Exception as e:
        logger.error(f"获取折线图数据失败: {e}")
        return {'code': 500, 'message': f'数据查询异常: {str(e)}', 'data': None}


MARKET_DATA_PATH = str(settings.DATA_DIR / 'market_data.json')
CAPITAL_FLOW_PATH = str(settings.DATA_DIR / 'capital_flow.json')


def _load_market_data() -> Dict[str, Any]:
    """加载行情数据文件。"""
    try:
        if not os.path.exists(MARKET_DATA_PATH):
            logger.warning(f"行情数据文件不存在: {MARKET_DATA_PATH}")
            return {}
        with open(MARKET_DATA_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载行情数据失败: {e}")
        return {}


async def get_market_data(sector: Optional[str] = None) -> Dict[str, Any]:
    """获取行情数据（ETF + 基准指数）。"""
    try:
        data = _load_market_data()
        if not data:
            return {'code': 200, 'data': None, 'message': '无行情数据'}

        result = {
            'benchmark_indices': data.get('benchmark_indices', {}),
            'last_update': data.get('last_update'),
        }

        etf_data = data.get('etf_data', {})
        if sector and sector in etf_data:
            result['etf_data'] = {sector: etf_data[sector]}
        else:
            result['etf_data'] = etf_data

        return {'code': 200, 'data': result}
    except Exception as e:
        logger.error(f"获取行情数据失败: {e}")
        return {'code': 500, 'message': str(e), 'data': None}


async def get_etf_correlation(sector: str, days: int = 30) -> Dict[str, Any]:
    """计算板块情绪指数与 ETF 价格的 Pearson 相关系数。"""
    try:
        market_data = _load_market_data()
        etf_data = market_data.get('etf_data', {}).get(sector, [])
        if not etf_data:
            return {'code': 200, 'data': None, 'message': '无行情数据'}

        json_history = _load_history_from_json()
        sentiment_data = json_history.get(sector, [])
        if not sentiment_data:
            return {'code': 200, 'data': None, 'message': '无情绪指数历史数据'}

        sentiment_map = {item['date']: item['value'] for item in sentiment_data}
        etf_map = {r['date']: r['close'] for r in etf_data}

        common_dates = sorted(set(sentiment_map.keys()) & set(etf_map.keys()))
        if len(common_dates) < 3:
            return {'code': 200, 'data': None, 'message': '共同日期不足（<3天），无法计算相关性'}

        sentiments = [sentiment_map[d] for d in common_dates]
        prices = [etf_map[d] for d in common_dates]

        n = len(sentiments)
        mean_s = sum(sentiments) / n
        mean_p = sum(prices) / n
        cov = sum((sentiments[i] - mean_s) * (prices[i] - mean_p) for i in range(n))
        std_s = (sum((s - mean_s) ** 2 for s in sentiments) / n) ** 0.5
        std_p = (sum((p - mean_p) ** 2 for p in prices) / n) ** 0.5

        if std_s == 0 or std_p == 0:
            correlation = 0.0
        else:
            correlation = round(cov / (n * std_s * std_p), 4)

        return {
            'code': 200,
            'data': {
                'sector': sector,
                'correlation': correlation,
                'common_dates': len(common_dates),
                'date_range': f'{common_dates[0]} ~ {common_dates[-1]}',
                'interpretation': (
                    '强正相关（情绪指数涨→ETF涨）' if correlation > 0.5
                    else '弱正相关' if correlation > 0.2
                    else '弱负相关' if correlation > -0.2
                    else '中等负相关' if correlation > -0.5
                    else '强负相关（情绪指数涨→ETF跌）'
                ),
            }
        }
    except Exception as e:
        logger.error(f"计算ETF相关性失败 [{sector}]: {e}")
        return {'code': 500, 'message': str(e), 'data': None}


def _load_capital_flow() -> Dict[str, Any]:
    """加载市场异动数据文件。"""
    try:
        if not os.path.exists(CAPITAL_FLOW_PATH):
            logger.warning(f"市场异动数据文件不存在: {CAPITAL_FLOW_PATH}")
            return {}
        with open(CAPITAL_FLOW_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载市场异动数据失败: {e}")
        return {}


async def get_capital_flow_summary() -> Dict[str, Any]:
    """获取市场异动数据概览（涨停池 + 龙虎榜统计）。"""
    try:
        data = _load_capital_flow()
        if not data:
            return {'code': 200, 'data': None, 'message': '无市场异动数据'}

        lu_data = data.get('limit_up_pool', {}).get('data', [])
        dtl_data = data.get('dragon_tiger_list', {}).get('data', [])

        lu_days = len(lu_data)
        lu_total = sum(len(d.get('stocks', [])) for d in lu_data)
        dtl_days = len(dtl_data)
        dtl_total = sum(len(d.get('stocks', [])) for d in dtl_data)

        latest_lu = lu_data[-1] if lu_data else None
        latest_dtl = dtl_data[-1] if dtl_data else None

        return {
            'code': 200,
            'data': {
                'limit_up_pool': {
                    'total_days': lu_days,
                    'total_stocks': lu_total,
                    'latest_date': latest_lu.get('date') if latest_lu else None,
                    'latest_count': len(latest_lu.get('stocks', [])) if latest_lu else 0,
                },
                'dragon_tiger_list': {
                    'total_days': dtl_days,
                    'total_stocks': dtl_total,
                    'latest_date': latest_dtl.get('date') if latest_dtl else None,
                    'latest_count': len(latest_dtl.get('stocks', [])) if latest_dtl else 0,
                },
                'last_update': data.get('last_update'),
                'update_count': data.get('update_count', 0),
            }
        }
    except Exception as e:
        logger.error(f"获取市场异动概览失败: {e}")
        return {'code': 500, 'message': str(e), 'data': None}


async def get_capital_flow_detail(data_type: str, trade_date: Optional[str] = None) -> Dict[str, Any]:
    """获取指定类型和日期的市场异动明细。"""
    try:
        data = _load_capital_flow()
        if not data:
            return {'code': 200, 'data': None, 'message': '无市场异动数据'}

        if data_type == 'limit_up':
            items = data.get('limit_up_pool', {}).get('data', [])
        elif data_type == 'dragon_tiger':
            items = data.get('dragon_tiger_list', {}).get('data', [])
        else:
            return {'code': 400, 'message': f'无效的数据类型: {data_type}（应为 limit_up 或 dragon_tiger）', 'data': None}

        if trade_date:
            target = next((d for d in items if d.get('date') == trade_date), None)
            if not target:
                return {'code': 200, 'data': None, 'message': f'未找到 {trade_date} 的数据'}
        else:
            target = items[-1] if items else None
            if not target:
                return {'code': 200, 'data': None, 'message': '无可用数据'}

        return {'code': 200, 'data': target}
    except Exception as e:
        logger.error(f"获取市场异动明细失败 [{data_type}/{trade_date}]: {e}")
        return {'code': 500, 'message': str(e), 'data': None}


class _DataService:
    get_dashboard_overview = staticmethod(get_dashboard_overview)
    _compute_dashboard_overview = staticmethod(_compute_dashboard_overview)


data_service = _DataService()
