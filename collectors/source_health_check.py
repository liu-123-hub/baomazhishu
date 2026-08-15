import asyncio
import os
import socket
import time
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

import httpx

from collectors.registry import PROBE_CONFIG


async def _probe_http_head(name: str, url: str, timeout: float, expected_status) -> Dict:
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
    tasks = []
    for name, cfg in PROBE_CONFIG.items():
        method = cfg["method"]
        timeout = cfg.get("timeout", 3.0)
        if method == "http_head":
            tasks.append(_probe_http_head(name, cfg["url"], timeout, cfg["expected_status"]))
        elif method == "env_key":
            tasks.append(_probe_env_key(name, cfg["env_key"], cfg["fallback_url"], timeout))

    results = await asyncio.gather(*tasks, return_exceptions=False)
    return list(results)


def get_reachable_sources(results: List[Dict]) -> List[str]:
    return [r["name"] for r in results if r["status"] == "reachable"]


def get_summary(results: List[Dict]) -> Dict:
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
    results = await check_source_connectivity()
    summary = get_summary(results)
    return {
        "status": "healthy" if summary["reachable"] > 0 else "critical",
        "summary": summary,
        "details": results,
    }
