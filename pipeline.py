"""宝妈指数主流程：采集→分析→计算→存储→输出。"""
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(__file__))

from collectors.guba_collector import collect_all as collect_guba
from collectors.xhs_collector import collect_all as collect_xhs
from collectors.google_news_collector import collect_all as collect_google_news
from collectors.netease_finance_collector import collect_all as collect_netease
from collectors.xueqiu_collector import collect_all as collect_xueqiu
from collectors.ths_finance_collector import collect_all as collect_ths
from collectors.xueqiu_community_collector import collect_all as collect_xueqiu_community
from collectors.market_data_collector import collect_all as collect_market_data, validate_market_data
from collectors.capital_flow_collector import collect_all as collect_capital_flow, validate_capital_flow
from collectors.data_validation import validate_source_posts
from collectors.data_authenticator import (
    authenticate_collected_data,
    build_data_provenance,
)
from analyzer.rule_based_analyzer import analyze_all
from analyzer.index_calculator import (
    compute_sector_index, add_record, get_dashboard_data, load_history, save_history, SECTOR_NAMES
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


class DataSourceStatus:
    """数据源状态追踪器。"""
    
    def __init__(self):
        self.sources: Dict[str, Dict] = {}
    
    def add_source(self, name: str, status: str, count: int = 0, error: str = "", duration: float = 0.0):
        self.sources[name] = {
            "name": name,
            "status": status,
            "count": count,
            "error": error,
            "duration": round(duration, 2),
        }
    
    def get_summary(self) -> str:
        lines = []
        total_count = 0
        for name, info in self.sources.items():
            status_icon = {
                "success": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "partial": "⚠️",
            }.get(info["status"], "❓")
            count_str = f"{info['count']}条" if info["count"] > 0 else ""
            time_str = f"({info['duration']}s)" if info["duration"] > 0 else ""
            error_str = f" — {info['error']}" if info["error"] else ""
            lines.append(f"  {status_icon} {name}: {count_str} {time_str}{error_str}")
            total_count += info["count"]
        lines.append(f"  📊 总计: {total_count} 条真实数据")
        return "\n".join(lines)
    
    def has_data(self) -> bool:
        return any(info["count"] > 0 for info in self.sources.values())


def _merge_sector_posts(
    all_posts: Dict,
    source_name: str,
    source_posts: Dict,
    auth_reports: List,
    display_name: str,
    duration_ms: Optional[float] = None,
    http_latency_ms: Optional[float] = None,
) -> int:
    cleaned_posts, issues = validate_source_posts(source_name, source_posts)

    issue_count = len([i for i in issues if "缺少字段" in i or "数据已过期" in i or "重复" in i])
    if issue_count > 0:
        print(f"  [校验] 发现 {issue_count} 个问题（详情见日志）")
    for issue in issues:
        print(f"    - {issue}")

    auth_report = authenticate_collected_data(
        display_name, cleaned_posts,
        duration_ms=duration_ms,
        http_latency_ms=http_latency_ms,
    )
    auth_reports.append(auth_report)
    if not auth_report["passed"]:
        print(f"  [真实性校验] ❌ 数据源「{display_name}」校验未通过:")
        for issue in auth_report["issues"]:
            print(f"    - {issue}")

    valid_count = 0
    for sector, posts in cleaned_posts.items():
        all_posts.setdefault(sector, [])
        all_posts[sector].extend(posts)
        valid_count += len(posts)

    return valid_count


def _write_dashboard_data(dashboard: Dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    dashboard_file = os.path.join(DATA_DIR, "dashboard_data.json")
    tmp_file = dashboard_file + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(dashboard, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, dashboard_file)
    print(f"  💾 数据已保存: {dashboard_file}")


def run_pipeline() -> Dict:
    """执行完整的数据采集→分析→指数计算流程。"""
    print("=" * 65)
    print("   👩‍👧 宝妈指数 · 真实数据采集与分析")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)
    
    status_tracker = DataSourceStatus()
    auth_reports: List = []
    health_latency_map: Dict[str, float] = {}

    print("\n🔌 第0步: 数据源连通性预检")
    print("-" * 45)
    try:
        import asyncio as _asyncio
        from collectors.source_health_check import run_health_check
        loop = _asyncio.new_event_loop()
        try:
            health_result = loop.run_until_complete(run_health_check())
        finally:
            loop.close()
        summary = health_result["summary"]
        print(f"  可达: {summary['reachable']}/{summary['total']}，"
              f"不可达: {summary['unreachable']}，跳过: {summary['skipped']}")
        for d in health_result["details"]:
            icon = {"reachable": "✅", "unreachable": "❌", "skipped": "⏭️"}.get(d["status"], "❓")
            latency = f"({d['latency_ms']}ms)" if d["latency_ms"] else ""
            err = f" — {d['error']}" if d["error"] else ""
            print(f"    {icon} {d['name']}{latency}{err}")
            if d.get("latency_ms") is not None:
                health_latency_map[d["name"]] = d["latency_ms"]
        if summary["all_unreachable"]:
            print("\n  ⚠️ 所有数据源均不可达，但仍尝试执行采集（可能为预检误判）")
    except Exception as e:
        print(f"  ⚠️ 连通性预检异常（不阻断采集）: {e}")

    print("\n📡 第1步: 真实数据采集")
    print("-" * 45)

    all_posts: Dict[str, List] = {}

    print("\n  [1/9] 东方财富股吧")
    guba_start = time.time()
    try:
        guba_data = collect_guba()
        guba_duration = time.time() - guba_start
        guba_count = _merge_sector_posts(
            all_posts, "guba", guba_data, auth_reports, "东方财富股吧",
            duration_ms=guba_duration * 1000,
            http_latency_ms=health_latency_map.get("东方财富股吧"),
        )
        status_tracker.add_source(
            "东方财富股吧",
            "success" if guba_count > 0 else "partial",
            guba_count,
            duration=guba_duration
        )
    except Exception as e:
        guba_duration = time.time() - guba_start
        status_tracker.add_source("东方财富股吧", "failed", 0, str(e), guba_duration)
        print(f"  ❌ 东方财富股吧采集失败: {e}")

    print("\n  [2/9] 小红书")
    xhs_start = time.time()
    try:
        xhs_data = collect_xhs()
        xhs_duration = time.time() - xhs_start
        xhs_count = _merge_sector_posts(
            all_posts, "xiaohongshu", xhs_data, auth_reports, "小红书",
            duration_ms=xhs_duration * 1000,
            http_latency_ms=health_latency_map.get("小红书"),
        )
        xhs_has_key = os.environ.get("RNODE_API_KEY", "") != ""
        if xhs_has_key:
            status = "success" if xhs_count > 0 else "partial"
        else:
            status = "skipped"
        status_tracker.add_source(
            "小红书",
            status,
            xhs_count,
            error="" if xhs_has_key else "未配置API Key",
            duration=xhs_duration
        )
    except Exception as e:
        xhs_duration = time.time() - xhs_start
        status_tracker.add_source("小红书", "failed", 0, str(e), xhs_duration)
        print(f"  ❌ 小红书采集失败: {e}")

    print("\n  [3/9] Google News RSS")
    gnews_start = time.time()
    try:
        google_news_data = collect_google_news()
        gnews_duration = time.time() - gnews_start
        gnews_count = _merge_sector_posts(
            all_posts, "google_news_rss", google_news_data, auth_reports, "Google News",
            duration_ms=gnews_duration * 1000,
            http_latency_ms=health_latency_map.get("Google News"),
        )
        status_tracker.add_source(
            "Google News",
            "success" if gnews_count > 0 else "partial",
            gnews_count,
            duration=gnews_duration
        )
    except Exception as e:
        gnews_duration = time.time() - gnews_start
        status_tracker.add_source("Google News", "failed", 0, str(e), gnews_duration)
        print(f"  ❌ Google News采集失败: {e}")

    print("\n  [4/9] 网易财经 RSS")
    netease_start = time.time()
    try:
        netease_data = collect_netease()
        netease_duration = time.time() - netease_start
        netease_count = _merge_sector_posts(
            all_posts, "netease_finance_rss", netease_data, auth_reports, "网易财经",
            duration_ms=netease_duration * 1000,
            http_latency_ms=health_latency_map.get("网易财经"),
        )
        status_tracker.add_source(
            "网易财经",
            "success" if netease_count > 0 else "partial",
            netease_count,
            duration=netease_duration
        )
    except Exception as e:
        netease_duration = time.time() - netease_start
        status_tracker.add_source("网易财经", "failed", 0, str(e), netease_duration)
        print(f"  ❌ 网易财经采集失败: {e}")

    print("\n  [5/9] 东方财富资讯")
    xq_start = time.time()
    try:
        xq_data = collect_xueqiu()
        xq_duration = time.time() - xq_start
        xq_count = _merge_sector_posts(
            all_posts, "eastmoney_news", xq_data, auth_reports, "东方财富资讯",
            duration_ms=xq_duration * 1000,
            http_latency_ms=health_latency_map.get("东方财富资讯"),
        )
        status_tracker.add_source(
            "东方财富资讯",
            "success" if xq_count > 0 else "partial",
            xq_count,
            duration=xq_duration
        )
    except Exception as e:
        xq_duration = time.time() - xq_start
        status_tracker.add_source("东方财富资讯", "failed", 0, str(e), xq_duration)
        print(f"  ❌ 东方财富资讯采集失败: {e}")

    print("\n  [6/9] 同花顺财经")
    ths_start = time.time()
    try:
        ths_data = collect_ths()
        ths_duration = time.time() - ths_start
        ths_count = _merge_sector_posts(
            all_posts, "ths_finance", ths_data, auth_reports, "同花顺财经",
            duration_ms=ths_duration * 1000,
            http_latency_ms=health_latency_map.get("同花顺财经"),
        )
        status_tracker.add_source(
            "同花顺财经",
            "success" if ths_count > 0 else "partial",
            ths_count,
            duration=ths_duration
        )
    except Exception as e:
        ths_duration = time.time() - ths_start
        status_tracker.add_source("同花顺财经", "failed", 0, str(e), ths_duration)
        print(f"  ❌ 同花顺财经采集失败: {e}")

    print("\n  [7/9] 雪球社区")
    xq_community_start = time.time()
    try:
        xq_community_data = collect_xueqiu_community()
        xq_community_duration = time.time() - xq_community_start
        xq_community_count = _merge_sector_posts(
            all_posts, "xueqiu_community", xq_community_data, auth_reports, "雪球社区",
            duration_ms=xq_community_duration * 1000,
            http_latency_ms=health_latency_map.get("雪球社区"),
        )
        status_tracker.add_source(
            "雪球社区",
            "success" if xq_community_count > 0 else "partial",
            xq_community_count,
            duration=xq_community_duration
        )
    except Exception as e:
        xq_community_duration = time.time() - xq_community_start
        status_tracker.add_source("雪球社区", "failed", 0, str(e), xq_community_duration)
        print(f"  ❌ 雪球社区采集失败: {e}")

    print("\n  [8/9] 行情数据 (AKShare)")
    market_data: Dict = {}
    market_start = time.time()
    try:
        market_data = collect_market_data()
        market_duration = time.time() - market_start
        market_etf_count = sum(len(v) for v in market_data.get("etf_data", {}).values())
        market_idx_count = len(market_data.get("benchmark_indices", {}))
        status_tracker.add_source(
            "行情数据(AKShare)",
            "success" if market_etf_count > 0 else "partial",
            market_etf_count,
            duration=market_duration
        )
        print(f"     ETF板块: {len(market_data.get('etf_data', {}))}个, 基准指数: {market_idx_count}个")
    except Exception as e:
        market_duration = time.time() - market_start
        status_tracker.add_source("行情数据(AKShare)", "failed", 0, str(e), market_duration)
        print(f"  ❌ 行情数据采集失败: {e}")

    print("\n  [9/9] 市场异动数据 (AKShare)")
    capital_flow_data: Dict = {}
    cf_start = time.time()
    try:
        capital_flow_data = collect_capital_flow()
        cf_duration = time.time() - cf_start
        lu_days = len(capital_flow_data.get("limit_up_pool", {}).get("data", []))
        lu_stocks = sum(
            len(d.get("stocks", []))
            for d in capital_flow_data.get("limit_up_pool", {}).get("data", [])
        )
        dtl_days = len(capital_flow_data.get("dragon_tiger_list", {}).get("data", []))
        dtl_stocks = sum(
            len(d.get("stocks", []))
            for d in capital_flow_data.get("dragon_tiger_list", {}).get("data", [])
        )
        status_tracker.add_source(
            "市场异动数据(AKShare)",
            "success" if lu_days > 0 or dtl_days > 0 else "partial",
            lu_stocks + dtl_stocks,
            duration=cf_duration
        )
        print(f"     涨停池: {lu_days}天/{lu_stocks}只, 龙虎榜: {dtl_days}天/{dtl_stocks}只")
    except Exception as e:
        cf_duration = time.time() - cf_start
        status_tracker.add_source("市场异动数据(AKShare)", "failed", 0, str(e), cf_duration)
        print(f"  ❌ 市场异动数据采集失败: {e}")

    print("\n" + "-" * 45)
    print("  📋 数据源状态汇总:")
    print(status_tracker.get_summary())
    
    total_collected = sum(len(v) for v in all_posts.values())
    if total_collected == 0:
        print("\n❌ 所有数据源均未采集到数据，无法继续分析")
        raise RuntimeError("所有真实数据源均不可用，请检查网络连接或数据源配置")
    
    print(f"\n  📊 共采集 {total_collected} 条真实数据\n")
    
    print("🧠 第2步: 多维度分析")
    print("-" * 45)
    analysis_start = time.time()
    analysis_results = analyze_all(all_posts)
    analysis_duration = time.time() - analysis_start
    
    for sector, results in analysis_results.items():
        top_newbie = [r for r in results if r.newbie_score >= 30][:3]
        print(f"\n  [{SECTOR_NAMES.get(sector, sector)}] 共分析 {len(results)} 条")
        if top_newbie:
            print(f"  🔥 典型小白帖:")
            for r in top_newbie:
                print(f"     [{r.level} {r.newbie_score}分] {r.title[:50]}...")
    
    print(f"\n  ⏱️ 分析耗时: {round(analysis_duration, 2)}s")
    
    print("\n📊 第3步: 指数计算")
    print("-" * 45)
    
    sector_indices = {}
    for sector, results in analysis_results.items():
        result = compute_sector_index(results)
        sector_indices[sector] = result
        name = SECTOR_NAMES.get(sector, sector)
        d = result["details"]
        bar = "█" * int(result["index"] / 5) + "░" * (20 - int(result["index"] / 5))
        print(f"  {name:6s} {bar} {result['index']:5.1f}  [{d['newbie_posts']}/{d['total_posts']}小白, {d['newbie_ratio']}%]")
    
    print("\n💾 第4步: 存储历史记录")
    print("-" * 45)
    add_record(sector_indices, analysis_results)
    print("  ✅ 历史记录已更新")
    
    print("\n🌐 第5步: 生成前端数据")
    print("-" * 45)

    print("\n  🔗 执行URL抽样可达性验证...")
    url_validation = {"enabled": False, "status": "skipped"}
    try:
        from collectors.url_validator import validate_urls
        url_validation = validate_urls(all_posts, sample_size=5, timeout=6)
        print(f"  URL验证: 抽样{url_validation['sample_size']}个, "
              f"可达{url_validation['reachable_count']}, "
              f"不可达{url_validation['unreachable_count']}, "
              f"可达率{url_validation['reachability_ratio'] or 'N/A'}")
        if url_validation["status"] == "degraded":
            print("  ⚠️ URL可达率偏低，可能部分链接已失效")
        elif url_validation["status"] == "critical":
            print("  ❌ URL可达率严重偏低，数据源可能存在问题")
    except Exception as e:
        print(f"  ⚠️ URL验证异常（不阻断）: {e}")

    dashboard = get_dashboard_data()
    
    dashboard["data_sources"] = status_tracker.sources
    dashboard["generated_at"] = datetime.now().isoformat()

    total_records = sum(len(v) for v in all_posts.values())
    dashboard["data_provenance"] = build_data_provenance(auth_reports, total_records)
    dashboard["is_real_data"] = dashboard["data_provenance"].get("is_real_data", False)

    market_validation = validate_market_data(market_data)
    capital_validation = validate_capital_flow(capital_flow_data)
    dashboard["data_quality"] = {
        "market_data": market_validation,
        "capital_flow": capital_validation,
        "url_validation": url_validation,
        "checked_at": datetime.now().isoformat(),
    }
    total_quality_issues = (
        len(market_validation.get("issues", [])) +
        len(capital_validation.get("issues", []))
    )
    if url_validation.get("unreachable_count", 0) > 0:
        total_quality_issues += url_validation["unreachable_count"]
    if total_quality_issues > 0:
        print(f"\n  ⚠️ 数据质量校验发现 {total_quality_issues} 个问题（已记录，不阻断）")

    _write_dashboard_data(dashboard)
    
    print("\n" + "=" * 65)
    print("   ✅ 分析完成!")
    print(f"   📅 历史记录: {dashboard['record_count']} 天")
    print(f"   🔢 今日数据: {total_records} 条真实帖子")
    if dashboard["latest"]:
        print()
        for sector, data in dashboard["latest"]["sectors"].items():
            name = SECTOR_NAMES.get(sector, sector)
            print(f"   {name}: {data['index']} — {data['interpretation']}")
    print("=" * 65)
    
    return dashboard


if __name__ == "__main__":  # pragma: no cover
    try:
        dashboard = run_pipeline()
    except RuntimeError as e:
        print(f"\n❌ 运行失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
