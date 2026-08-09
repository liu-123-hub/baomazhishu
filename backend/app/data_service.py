"""数据服务层：大盘数据计算与历史趋势查询。"""
import time
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

_DATA_FRESHNESS_MAX_HOURS = 72
_DEGRADED_THRESHOLD_SECONDS = _DATA_FRESHNESS_MAX_HOURS * 3600


def _parse_iso_time(time_str: Optional[str]) -> Optional[datetime]:
    if not time_str:
        return None
    try:
        if 'T' in time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            if dt.tzinfo is not None:
                import time as _time
                return datetime.fromtimestamp(dt.timestamp())
            return dt
        return datetime.strptime(time_str[:19], '%Y-%m-%d %H:%M:%S') if ' ' in time_str else datetime.strptime(time_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        try:
            return datetime.strptime(time_str[:10], '%Y-%m-%d')
        except (ValueError, TypeError):
            return None


def _compute_is_degraded(
    update_time: Optional[str],
    source_passed: Optional[bool] = None,
    user_discussion_present: Optional[bool] = None,
    json_provenance_time: Optional[str] = None,
    has_valid_data: Optional[bool] = None,
) -> bool:
    """判断板块是否降级：真实性校验失败/无有效数据/超过72h。"""
    if source_passed is False:
        return True

    if has_valid_data is False:
        return True

    if update_time:
        update_dt = _parse_iso_time(update_time)
        if update_dt is None:
            return True
        now = datetime.now()
        age_seconds = (now - update_dt).total_seconds()
        if age_seconds > _DEGRADED_THRESHOLD_SECONDS:
            return True

    return False


def _load_from_json_file() -> Dict[str, Any]:
    try:
        if not os.path.exists(JSON_DATA_PATH):
            logger.warning(f"JSON 数据文件不存在: {JSON_DATA_PATH}")
            return {'sectors': {}, 'timestamp': None, 'date': None}
        with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not data or not isinstance(data, dict):
            logger.warning("JSON 数据文件格式异常")
            return {'sectors': {}, 'timestamp': None, 'date': None}
        latest = data.get('latest', {})
        if not isinstance(latest, dict):
            return {'sectors': {}, 'timestamp': None, 'date': None}
        return {
            'sectors': latest.get('sectors', {}) or {},
            'timestamp': latest.get('timestamp'),
            'date': latest.get('date'),
        }
    except json.JSONDecodeError as e:
        logger.error(f"JSON 数据文件解析失败: {e}")
        return {'sectors': {}, 'timestamp': None, 'date': None}
    except Exception as e:
        logger.error(f"加载 JSON 数据文件异常: {e}")
        return {'sectors': {}, 'timestamp': None, 'date': None}


def _load_history_from_json() -> Dict[str, List[Dict]]:
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
                details = sector_data.get('details', {}) if isinstance(sector_data.get('details'), dict) else {}
                total_posts = details.get('total_posts', 0) or 0
                if value_float <= 0 and total_posts > 0:
                    continue
                if total_posts <= 0 and value_float == 0:
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


def _load_data_quality() -> Dict[str, Any]:
    try:
        if not os.path.exists(JSON_DATA_PATH):
            return {'available': False, 'reason': '数据文件尚未生成'}
        with open(JSON_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {'available': False, 'reason': '数据文件格式异常'}
        quality = data.get('data_quality')
        if not quality:
            return {'available': False, 'reason': '数据文件中未包含质量校验信息'}
        return {'available': True, **quality}
    except Exception as e:
        logger.error(f"加载数据质量校验信息失败: {e}")
        return {'available': False, 'reason': f'加载异常: {str(e)}'}


def _load_data_provenance() -> Dict[str, Any]:
    """加载数据溯源信息，兼容新旧数据格式。"""
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

        result = {'available': True, **provenance}

        if 'has_user_discussion' not in result:
            fingerprints_list = result.get('fingerprints', [])
            user_sources = {'东方财富股吧', '雪球社区', '小红书'}
            user_discussion_reports = []
            if isinstance(fingerprints_list, list):
                user_discussion_reports = [
                    fp for fp in fingerprints_list
                    if isinstance(fp, dict) and fp.get('source_name') in user_sources
                ]
            user_discussion_passed = [
                fp for fp in user_discussion_reports
                if fp.get('passed') and fp.get('record_count', 0) > 0
            ]
            result['has_user_discussion'] = len(user_discussion_passed) > 0
            result['user_discussion_count'] = len(user_discussion_passed)
            result['user_discussion_total'] = len(user_discussion_reports)
            result['_legacy_format'] = True

        return result
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
        return 50.0
    return round(buy / total * 100, 1)


def _map_sector_row(
    row: Dict,
    history: Optional[List[Dict]] = None,
    json_provenance_time: Optional[str] = None,
    global_has_user_discussion: Optional[bool] = None,
) -> Dict[str, Any]:
    """将数据库行映射为前端字段格式。"""
    buy = float(row.get('buy_index', 0) or 0)
    sell = float(row.get('sell_index', 0) or 0)
    total_sentiment = buy + sell
    raw_index = row.get('index_value', 0)
    try:
        index_value = round(float(raw_index), 1) if raw_index is not None else None
    except (TypeError, ValueError):
        index_value = None

    post_count = int(row.get('total_posts', 0) or 0)
    update_time = _format_update_time(row.get('created_at') or row.get('record_date'))

    has_valid_data = index_value is not None and post_count > 0
    user_discussion_raw = row.get('user_discussion_present')
    user_discussion_present = bool(user_discussion_raw) if user_discussion_raw is not None else global_has_user_discussion
    source_passed_raw = row.get('source_passed')
    source_passed = bool(source_passed_raw) if source_passed_raw is not None else None

    is_degraded = _compute_is_degraded(
        update_time=update_time,
        source_passed=source_passed,
        user_discussion_present=user_discussion_present,
        json_provenance_time=json_provenance_time,
        has_valid_data=has_valid_data,
    )

    buy_count = int(row.get('buy_count', 0) or 0)
    sell_count = int(row.get('sell_count', 0) or 0)
    if buy_count == 0 and sell_count == 0 and total_sentiment > 0:
        buy_count = int(round(buy / total_sentiment * post_count)) if post_count > 0 else 0
        sell_count = post_count - buy_count if post_count > 0 else 0

    sector_code = row.get('sector_code')
    return {
        'code': sector_code,
        'name': row.get('sector_name') or settings.SECTOR_NAMES.get(sector_code, sector_code),
        'index': index_value,
        'post_count': post_count,
        'positive_ratio': _compute_positive_ratio(row),
        'buy': buy_count,
        'sell': sell_count,
        'buy_index': buy,
        'sell_index': sell,
        'trend': _compute_trend(history) if history else '平稳',
        'update_time': update_time,
        'is_degraded': is_degraded,
    }


def _map_json_sector(
    code: str,
    data: Dict,
    json_history_map: Dict[str, List[Dict]],
    json_provenance_time: Optional[str] = None,
    global_has_user_discussion: Optional[bool] = None,
    global_update_time: Optional[str] = None,
) -> Dict[str, Any]:
    """将JSON板块数据映射为前端格式。"""
    details = data.get('details', {}) if isinstance(data.get('details'), dict) else {}
    buy = float(details.get('mom_buy_index', 0) or data.get('mom_buy_index', 0) or 0)
    sell = float(details.get('mom_sell_index', 0) or data.get('mom_sell_index', 0) or 0)
    total = buy + sell
    positive_ratio = round(buy / total * 100, 1) if total > 0 else 50.0

    update_time = (
        data.get('update_time')
        or data.get('timestamp')
        or global_update_time
        or (data.get('date') if isinstance(data.get('date'), str) else None)
    )

    merged_history = _build_merged_history_for_trend(code, [], json_history_map)
    raw_index = data.get('index', 0)
    try:
        index_value = round(float(raw_index), 1) if raw_index is not None else None
    except (TypeError, ValueError):
        index_value = None

    post_count = int(details.get('total_posts', data.get('total_posts', 0)) or 0)
    has_valid_data = index_value is not None and post_count > 0

    is_degraded = _compute_is_degraded(
        update_time=update_time,
        user_discussion_present=global_has_user_discussion,
        json_provenance_time=json_provenance_time,
        has_valid_data=has_valid_data,
    )

    buy_count = 0
    sell_count = 0
    if buy_count_key := details.get('buy_count') or data.get('buy_count'):
        buy_count = int(buy_count_key)
    if sell_count_key := details.get('sell_count') or data.get('sell_count'):
        sell_count = int(sell_count_key)
    if buy_count == 0 and sell_count == 0 and total > 0:
        buy_count = int(round(buy / (buy + sell) * post_count)) if post_count > 0 else 0
        sell_count = post_count - buy_count if post_count > 0 else 0

    return {
        'code': code,
        'name': settings.SECTOR_NAMES.get(code, code),
        'index': index_value,
        'post_count': post_count,
        'positive_ratio': positive_ratio,
        'buy': buy_count,
        'sell': sell_count,
        'buy_index': buy,
        'sell_index': sell,
        'trend': _compute_trend(merged_history),
        'update_time': update_time,
        'is_degraded': is_degraded,
    }


async def _compute_dashboard_overview() -> Dict[str, Any]:
    """DB优先，JSON降级回补，双源融合策略。"""
    try:
        rows = await db.get_latest_sector_index()

        json_history_map = _load_history_from_json()
        json_data = _load_from_json_file()
        json_sectors = json_data.get('sectors', {})
        json_global_update_time = json_data.get('timestamp') or json_data.get('date')

        provenance = _load_data_provenance()
        json_provenance_time = None
        if provenance.get('available'):
            fingerprints = provenance.get('fingerprints', []) or []
            collected_ats = [
                fp.get('collected_at') for fp in fingerprints
                if isinstance(fp, dict) and fp.get('collected_at')
            ]
            if collected_ats:
                json_provenance_time = max(collected_ats)
        has_user_discussion = provenance.get('has_user_discussion') if provenance.get('available') else None

        sectors = {}
        if rows:
            for row in rows:
                code = row.get('sector_code')
                if not code or code not in VALID_SECTORS:
                    if code and code not in VALID_SECTORS:
                        logger.warning(f"数据库中存在未配置板块代码，已过滤: {code}")
                    continue
                db_history = await db.get_sector_history(code, days=7)
                merged_history = _build_merged_history_for_trend(code, db_history, json_history_map)
                sectors[code] = _map_sector_row(
                    row, merged_history,
                    json_provenance_time=json_provenance_time,
                    global_has_user_discussion=has_user_discussion,
                )

        for code in VALID_SECTORS:
            if code not in sectors and code in json_sectors:
                sector_data = _map_json_sector(
                    code, json_sectors[code], json_history_map,
                    json_provenance_time=json_provenance_time,
                    global_has_user_discussion=has_user_discussion,
                    global_update_time=json_global_update_time,
                )
                sectors[code] = sector_data

        if not sectors:
            for code in VALID_SECTORS:
                if code in json_sectors:
                    sector_data = _map_json_sector(
                        code, json_sectors[code], json_history_map,
                        json_provenance_time=json_provenance_time,
                        global_has_user_discussion=has_user_discussion,
                        global_update_time=json_global_update_time,
                    )
                    sectors[code] = sector_data

        degraded_sectors = [code for code, s in sectors.items() if s.get('is_degraded')]
        valid_sectors = {code: s for code, s in sectors.items() if not s.get('is_degraded')}

        sector_count = len(VALID_SECTORS)
        if sector_count == 0:
            avg_index = None
            last_update_time = None
        else:
            valid_for_calc = [s for s in valid_sectors.values() if isinstance(s, dict) and s.get('index') is not None]
            if not valid_for_calc:
                valid_for_calc = [s for s in sectors.values() if isinstance(s, dict) and s.get('index') is not None]
            total_index = sum(s['index'] for s in valid_for_calc)
            avg_index = round(total_index / len(valid_for_calc), 1) if valid_for_calc else None
            update_times = [s.get('update_time') for s in sectors.values() if isinstance(s, dict) and s.get('update_time')]
            last_update_time = max(update_times) if update_times else None

        from collectors.data_authenticator import is_data_fresh
        freshness = is_data_fresh(last_update_time, max_age_hours=_DATA_FRESHNESS_MAX_HOURS)

        quality = _load_data_quality()
        integrity_check = _validate_data_integrity(sectors, provenance, last_update_time)

        is_real_data = provenance.get('is_real_data', False) if isinstance(provenance, dict) else False
        if not is_real_data:
            has_valid_indices = any(
                isinstance(s, dict) and s.get('index') is not None
                for s in sectors.values()
            )
            is_real_data = has_valid_indices

        return {
            'code': 200,
            'data': {
                'avg_index': avg_index,
                'sector_count': sector_count,
                'last_update_time': last_update_time,
                'sectors': sectors,
                'degraded_sectors': degraded_sectors,
                'has_valid_user_discussion': has_user_discussion if has_user_discussion is not None else True,
                'valid_sector_count': len(valid_sectors),
                'is_real_data': is_real_data,
                'data_freshness': freshness,
                'data_provenance': provenance,
                'data_quality': quality,
                'data_integrity': integrity_check,
            }
        }
    except Exception as e:
        logger.error(f"计算大盘概览失败: {e}")
        return {
            'code': 500,
            'message': f'数据计算异常: {str(e)}',
            'data': None
        }


def _validate_data_integrity(
    sectors: Dict[str, Dict],
    provenance: Dict[str, Any],
    last_update_time: Optional[str],
) -> Dict[str, Any]:
    """数据真实性校验（字段级/完整性/一致性）。"""
    field_issues: List[str] = []
    integrity_issues: List[str] = []
    consistency_issues: List[str] = []

    for code, s in sectors.items():
        if not isinstance(s, dict):
            field_issues.append(f"板块 {code}: 数据非 dict 类型")
            continue
        index_val = s.get('index')
        if index_val is not None:
            if not isinstance(index_val, (int, float)):
                field_issues.append(f"板块 {code}: index 类型异常 ({type(index_val).__name__})")
            elif index_val < 0 or index_val > 100:
                field_issues.append(f"板块 {code}: index 超出 [0, 100] 范围 ({index_val})")
        post_count = s.get('post_count')
        if post_count is not None and (not isinstance(post_count, int) or post_count < 0):
            field_issues.append(f"板块 {code}: post_count 异常 ({post_count})")
        positive_ratio = s.get('positive_ratio')
        if positive_ratio is not None and (positive_ratio < 0 or positive_ratio > 100):
            field_issues.append(f"板块 {code}: positive_ratio 超出 [0, 100] 范围 ({positive_ratio})")

    if not sectors:
        integrity_issues.append("板块数据为空")
    missing_update_time = [code for code, s in sectors.items() if isinstance(s, dict) and not s.get('update_time')]
    if missing_update_time:
        integrity_issues.append(f"以下板块缺失 update_time: {', '.join(missing_update_time[:5])}")
    if provenance.get('available'):
        if 'is_real_data' not in provenance:
            integrity_issues.append("provenance 缺失 is_real_data 字段")
        if 'fingerprints' not in provenance:
            integrity_issues.append("provenance 缺失 fingerprints 字段")

    if sectors and last_update_time:
        last_dt = _parse_iso_time(last_update_time)
        if last_dt:
            for code, s in sectors.items():
                if not isinstance(s, dict):
                    continue
                s_time = s.get('update_time')
                if not s_time:
                    continue
                s_dt = _parse_iso_time(s_time)
                if s_dt and abs((last_dt - s_dt).total_seconds()) > _DEGRADED_THRESHOLD_SECONDS:
                    consistency_issues.append(
                        f"板块 {code}: update_time ({s_time}) 与全局 last_update_time ({last_update_time}) 偏差超 24h"
                    )

    consistency_issues = consistency_issues[:5]

    passed = not (field_issues or integrity_issues or consistency_issues)
    return {
        'passed': passed,
        'field_issues': field_issues,
        'integrity_issues': integrity_issues,
        'consistency_issues': consistency_issues,
        'checked_at': datetime.now().isoformat(),
    }


async def get_dashboard_overview() -> Dict[str, Any]:
    return await dashboard_cache.get_or_set('dashboard_overview', _compute_dashboard_overview, ttl=30)


async def _compute_sector_detail(code: str) -> Dict[str, Any]:
    if code not in VALID_SECTORS:
        logger.warning(f"请求了未配置的板块详情: {code}")
        return {
            'code': 400,
            'message': f'无效的板块代码: {code}',
            'data': None
        }
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

        json_data = _load_from_json_file()
        sectors = json_data.get('sectors', {})
        json_global_update_time = json_data.get('timestamp') or json_data.get('date')
        if code in sectors and isinstance(sectors[code], dict):
            return {
                'code': 200,
                'data': _map_json_sector(code, sectors[code], json_history_map, global_update_time=json_global_update_time)
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
    return await dashboard_cache.get_or_set(f'sector_detail_{code}', lambda: _compute_sector_detail(code), ttl=60)


async def _compute_history_trend(code: Optional[str], days: int = 7) -> Dict[str, Any]:
    """合并数据库与 history.json 数据。"""
    if code and code not in VALID_SECTORS:
        logger.warning(f"请求了未配置板块的历史趋势: {code}")
        return {
            'code': 400,
            'message': f'无效的板块代码: {code}',
            'data': None
        }
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
                    if r.get('record_date') is not None and r.get('index_value', 0) > 0
                ]
        else:
            result = await db.get_all_sectors_history(days=days)
            if result:
                for c, rows in result.items():
                    if c not in VALID_SECTORS:
                        logger.warning(f"历史数据中存在未配置板块代码，已过滤: {c}")
                        continue
                    db_history[c] = [
                        {'date': r.get('record_date'), 'value': r.get('index_value')}
                        for r in rows
                        if r.get('record_date') is not None and r.get('index_value', 0) > 0
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
    return await dashboard_cache.get_or_set(
        f'history_trend_{code}_{days}',
        lambda: _compute_history_trend(code, days),
        ttl=30
    )


async def get_all_sectors_history(days: int = 7) -> Dict[str, Any]:
    return await get_history_trend(None, days)


async def get_line_chart_data(sectors: str, days: int = 7) -> Dict[str, Any]:
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
        sector_names = settings.SECTOR_NAMES

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
                series_name = sector_names.get(code, code)
                series_data.append({
                    'name': series_name,
                    'code': code,
                    'data': [date_value_map.get(date) for date in x_axis]
                })
                legend.append(series_name)

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


# ── 指数比值面积图：创业板指 / 中证红利 ──────────────────────────────

# 两个基准指数的代码与显示名称
_RATIO_INDEX_A = 'sz399006'   # 创业板指
_RATIO_INDEX_B = 'sh000922'   # 中证红利
_RATIO_NAME_A = '创业板指'
_RATIO_NAME_B = '中证红利'


def _get_index_close_map(market_data: Dict, index_code: str) -> Dict[str, float]:
    """从行情数据中提取指定指数的 {date: close} 映射，按日期升序排列。"""
    indices = market_data.get('benchmark_indices', {})
    entry = indices.get(index_code)
    if not entry or not isinstance(entry, dict):
        return {}
    records = entry.get('data', [])
    if not isinstance(records, list):
        return {}
    close_map: Dict[str, float] = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        date_str = rec.get('date')
        close_val = rec.get('close')
        if not date_str or close_val is None:
            continue
        try:
            close_map[date_str] = float(close_val)
        except (TypeError, ValueError):
            continue
    return dict(sorted(close_map.items()))


def _align_and_fill(
    map_a: Dict[str, float],
    map_b: Dict[str, float],
) -> List[Dict[str, Any]]:
    """对齐两个指数的日期序列，前向填充缺失值，返回逐日对齐列表。

    返回格式: [{date, close_a, close_b}, ...]
    缺失值用上一个交易日的收盘价填充，确保比值计算不出现空值或跳点。
    """
    all_dates = sorted(set(map_a.keys()) | set(map_b.keys()))
    result: List[Dict[str, Any]] = []
    prev_a: Optional[float] = None
    prev_b: Optional[float] = None
    for date_str in all_dates:
        val_a = map_a.get(date_str)
        val_b = map_b.get(date_str)
        # 前向填充：当天缺失则沿用上一有效值
        if val_a is None:
            val_a = prev_a
        else:
            prev_a = val_a
        if val_b is None:
            val_b = prev_b
        else:
            prev_b = val_b
        # 两个值都有效才能计算比值
        if val_a is not None and val_b is not None and val_b != 0:
            result.append({
                'date': date_str,
                'close_a': val_a,
                'close_b': val_b,
            })
    return result


def _aggregate_by_unit(
    aligned: List[Dict[str, Any]],
    unit: str,
) -> List[Dict[str, Any]]:
    """按时间单位聚合，取每个周期最后一个交易日的收盘价。

    - year:    历年年度收盘比值
    - quarter: 各季度末收盘比值
    - month:   各月度收盘比值
    """
    if not aligned:
        return []

    # 将每条记录归类到对应周期键
    buckets: Dict[str, Dict[str, Any]] = {}
    for item in aligned:
        date_str = item['date']
        parts = date_str.split('-')
        if len(parts) < 3:
            continue
        year, month = parts[0], int(parts[1])
        if unit == 'year':
            key = year
        elif unit == 'quarter':
            q = (month - 1) // 3 + 1
            key = f'{year}-Q{q}'
        else:  # month
            key = f'{year}-{parts[1]}'
        # 每个周期保留最后一条（aligned 已按日期升序）
        buckets[key] = item

    # 按日期顺序输出
    return sorted(buckets.values(), key=lambda x: x['date'])


async def get_index_ratio_data(unit: str = 'month') -> Dict[str, Any]:
    """获取创业板指/中证红利比值面积图数据。

    参数:
        unit: 时间聚合单位 — 'year' | 'quarter' | 'month'

    返回:
        {
            'x_axis': ['2023-08', ...],
            'ratios': [0.4321, ...],
            'chinext_values': [2239.31, ...],
            'dividend_values': [5185.83, ...],
            'index_names': {'a': '创业板指', 'b': '中证红利'},
            'unit': 'month'
        }
    """
    valid_units = {'year', 'quarter', 'month'}
    if unit not in valid_units:
        return {'code': 400, 'message': f'无效的时间单位: {unit}（应为 year/quarter/month）', 'data': None}

    try:
        market_data = _load_market_data()
        if not market_data:
            return {'code': 200, 'data': None, 'message': '无行情数据'}

        map_a = _get_index_close_map(market_data, _RATIO_INDEX_A)
        map_b = _get_index_close_map(market_data, _RATIO_INDEX_B)

        if not map_a or not map_b:
            missing = []
            if not map_a:
                missing.append(_RATIO_NAME_A)
            if not map_b:
                missing.append(_RATIO_NAME_B)
            return {'code': 200, 'data': None, 'message': f'缺少指数数据: {", ".join(missing)}'}

        # 对齐日期 + 前向填充缺失值
        aligned = _align_and_fill(map_a, map_b)
        if not aligned:
            return {'code': 200, 'data': None, 'message': '无有效对齐数据'}

        # 按时间单位聚合
        aggregated = _aggregate_by_unit(aligned, unit)

        x_axis: List[str] = []
        ratios: List[float] = []
        chinext_values: List[float] = []
        dividend_values: List[float] = []

        for item in aggregated:
            close_a = item['close_a']
            close_b = item['close_b']
            ratio = round(close_a / close_b, 4)
            # X轴标签根据时间单位格式化
            date_str = item['date']
            parts = date_str.split('-')
            if unit == 'year':
                label = parts[0]
            elif unit == 'quarter':
                year = parts[0]
                month = int(parts[1])
                q = (month - 1) // 3 + 1
                label = f'{year}-Q{q}'
            else:
                label = f'{parts[0]}-{parts[1]}'
            x_axis.append(label)
            ratios.append(ratio)
            chinext_values.append(round(close_a, 2))
            dividend_values.append(round(close_b, 2))

        return {
            'code': 200,
            'data': {
                'x_axis': x_axis,
                'ratios': ratios,
                'chinext_values': chinext_values,
                'dividend_values': dividend_values,
                'index_names': {'a': _RATIO_NAME_A, 'b': _RATIO_NAME_B},
                'unit': unit,
            }
        }
    except Exception as e:
        logger.error(f"获取指数比值数据失败 [{unit}]: {e}")
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
    """获取市场异动数据概览。"""
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
    get_sector_detail = staticmethod(get_sector_detail)
    get_history_trend = staticmethod(get_history_trend)
    get_all_sectors_history = staticmethod(get_all_sectors_history)
    get_line_chart_data = staticmethod(get_line_chart_data)
    get_market_data = staticmethod(get_market_data)
    get_etf_correlation = staticmethod(get_etf_correlation)
    get_capital_flow_summary = staticmethod(get_capital_flow_summary)
    get_capital_flow_detail = staticmethod(get_capital_flow_detail)


data_service = _DataService()
