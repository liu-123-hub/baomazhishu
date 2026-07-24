"""数据源连通性预检模块，采集前探测各数据源可用性。"""
import asyncio
import os
import socket
import time
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

import httpx


_PROBE_CONFIG = {
    "东方财富股吧": {
        "method": "http_head",
        "url": "https://guba.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "小红书": {
        "method": "env_key",
        "env_key": "RNODE_API_KEY",
        "fallback_url": "https://rnote.dev/",
        "timeout": 3.0,
    },
    "雪球社区": {
        "method": "http_head",
        "url": "https://xueqiu.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302, 403),
    },
    "Google News": {
        "method": "http_head",
        "url": "https://news.google.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "网易财经": {
        "method": "http_head",
        "url": "https://finance.163.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "东方财富资讯": {
        "method": "http_head",
        "url": "https://finance.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "同花顺财经": {
        "method": "http_head",
        "url": "https://news.10jqka.com.cn/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "行情数据(AKShare)": {
        "method": "http_head",
        "url": "https://finance.sina.com.cn/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    "市场异动数据(AKShare)": {
        "method": "http_head",
        "url": "https://push2.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302, 404),
    },
}


async def _probe_http_head(name: str, url: str, timeout: float, expected_status) -> Dict:
    """通过 HTTP HEAD 请求探测数据源连通性。"""
    start = time.time()
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=True,
        ) as client:
            resp = await client.head(url, headers={"User-Agent": "mom-index-healthcheck/1.0"})
        latency = round((time.time() - start) * 1000, 1)
        if resp.status_code in expected_status:
            return {
                "name": name,
                "status": "reachable",
                "latency_ms": latency,
                "http_status": resp.status_code,
                "error": "",
                "checked_at": datetime.now().isoformat(),
            }
        return {
            "name": name,
            # 状态码不在预期集合内应标记为 unreachable，避免 pipeline 误判数据源可用
            "status": "unreachable",
            "latency_ms": latency,
            "http_status": resp.status_code,
            "error": f"非预期状态码 {resp.status_code}（预期 {expected_status}）",
            "checked_at": datetime.now().isoformat(),
        }
    except httpx.TimeoutException:
        return {
            "name": name,
            "status": "unreachable",
            "latency_ms": round((time.time() - start) * 1000, 1),
            "http_status": None,
            "error": f"连接超时（{timeout}s）",
            "checked_at": datetime.now().isoformat(),
        }
    except (httpx.ConnectError, httpx.NetworkError, socket.gaierror) as e:
        return {
            "name": name,
            "status": "unreachable",
            "latency_ms": round((time.time() - start) * 1000, 1),
            "http_status": None,
            "error": f"网络连接失败: {type(e).__name__}",
            "checked_at": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "name": name,
            "status": "unreachable",
            "latency_ms": round((time.time() - start) * 1000, 1),
            "http_status": None,
            "error": f"探测异常: {type(e).__name__}: {str(e)[:100]}",
            "checked_at": datetime.now().isoformat(),
        }


async def _probe_env_key(name: str, env_key: str, fallback_url: str, timeout: float) -> Dict:
    """依赖环境变量配置的数据源探测：先检查 Key 是否配置，再校验目标服务可达性。"""
    start = time.time()
    key_value = os.environ.get(env_key, "")
    if not key_value:
        return {
            "name": name,
            "status": "skipped",
            "latency_ms": 0,
            "http_status": None,
            "error": f"未配置环境变量 {env_key}，数据源已跳过",
            "checked_at": datetime.now().isoformat(),
        }
    return await _probe_http_head(name, fallback_url, timeout, (200, 301, 302))


async def check_source_connectivity() -> List[Dict]:
    """对所有数据源执行连通性预检。"""
    tasks = []
    for name, cfg in _PROBE_CONFIG.items():
        method = cfg["method"]
        timeout = cfg.get("timeout", 3.0)
        if method == "http_head":
            tasks.append(_probe_http_head(name, cfg["url"], timeout, cfg["expected_status"]))
        elif method == "env_key":
            tasks.append(_probe_env_key(name, cfg["env_key"], cfg["fallback_url"], timeout))

    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


def get_reachable_sources(results: List[Dict]) -> List[str]:
    """从探测结果中提取可达的数据源名称列表。"""
    return [r["name"] for r in results if r["status"] == "reachable"]


def get_summary(results: List[Dict]) -> Dict:
    """生成探测结果摘要。"""
    total = len(results)
    reachable = sum(1 for r in results if r["status"] == "reachable")
    unreachable = sum(1 for r in results if r["status"] == "unreachable")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    return {
        "total": total,
        "reachable": reachable,
        "unreachable": unreachable,
        "skipped": skipped,
        "all_unreachable": reachable == 0 and skipped != total,
        "checked_at": datetime.now().isoformat(),
    }


async def run_health_check() -> Dict:
    """执行完整的数据源连通性预检流程，返回包含详细结果与摘要的字典。"""
    results = await check_source_connectivity()
    summary = get_summary(results)
    return {
        "status": "healthy" if summary["reachable"] > 0 else "critical",
        "summary": summary,
        "details": results,
    }
