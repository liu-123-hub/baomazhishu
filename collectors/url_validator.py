"""新闻URL抽样可达性验证，确保链接真实可访问。"""
import random
import time
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse

import requests

DEFAULT_TIMEOUT = 8
DEFAULT_SAMPLE_SIZE = 5
MAX_RETRIES = 1
RETRY_DELAY = 1

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

SKIP_DOMAINS = frozenset({
    "www.xiaohongshu.com",
    "xiaohongshu.com",
    "xueqiu.com",
})


def _is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def _check_single_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
    result = {
        "url": url,
        "reachable": False,
        "status_code": None,
        "latency_ms": None,
        "error": None,
        "checked_at": None,
    }

    if not _is_valid_url(url):
        result["error"] = "invalid_url"
        return result

    parsed = urlparse(url)
    if parsed.netloc in SKIP_DOMAINS:
        result["error"] = "skipped_domain"
        result["reachable"] = True
        return result

    for attempt in range(MAX_RETRIES + 1):
        try:
            start = time.time()
            resp = requests.head(
                url,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
                allow_redirects=True,
            )
            latency_ms = round((time.time() - start) * 1000, 1)
            result["latency_ms"] = latency_ms
            result["status_code"] = resp.status_code
            result["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

            if resp.status_code < 400:
                result["reachable"] = True
                return result
            elif resp.status_code == 405:
                try:
                    start = time.time()
                    resp_get = requests.get(
                        url,
                        headers=DEFAULT_HEADERS,
                        timeout=timeout,
                        allow_redirects=True,
                        stream=True,
                    )
                    resp_get.close()
                    latency_ms = round((time.time() - start) * 1000, 1)
                    result["latency_ms"] = latency_ms
                    result["status_code"] = resp_get.status_code
                    result["reachable"] = resp_get.status_code < 400
                    return result
                except Exception:
                    pass
            if resp.status_code >= 500 and attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            break
        except requests.exceptions.Timeout:
            result["error"] = "timeout"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            break
        except requests.exceptions.SSLError:
            result["error"] = "ssl_error"
            break
        except requests.exceptions.ConnectionError:
            result["error"] = "connection_error"
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            break
        except Exception as e:
            result["error"] = f"{type(e).__name__}"
            break

    result["checked_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    return result


def sample_urls(
    all_posts: Dict[str, List[Dict]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> List[Tuple[str, str]]:
    urls = []
    for sector, posts in all_posts.items():
        for post in posts:
            url = post.get("url") or post.get("source_url") or post.get("link")
            source = post.get("platform", sector)
            if url and _is_valid_url(url):
                urls.append((source, url))

    if len(urls) <= sample_size:
        return urls

    return random.sample(urls, sample_size)


def validate_urls(
    all_posts: Dict[str, List[Dict]],
    sample_size: int = DEFAULT_SAMPLE_SIZE,
    timeout: int = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    samples = sample_urls(all_posts, sample_size)

    if not samples:
        return {
            "enabled": True,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "sample_size": 0,
            "total_urls_found": 0,
            "reachable_count": 0,
            "unreachable_count": 0,
            "skipped_count": 0,
            "reachability_ratio": None,
            "avg_latency_ms": None,
            "results": [],
            "status": "no_urls_found",
        }

    results = []
    for source, url in samples:
        r = _check_single_url(url, timeout)
        r["source_platform"] = source
        results.append(r)

    reachable = [r for r in results if r["reachable"] and r["error"] != "skipped_domain"]
    unreachable = [r for r in results if not r["reachable"] and r["error"] not in (None, "skipped_domain")]
    skipped = [r for r in results if r["error"] == "skipped_domain"]
    latencies = [r["latency_ms"] for r in results if r["latency_ms"] is not None]

    checked = len(results) - len(skipped)
    ratio = round(len(reachable) / checked, 3) if checked > 0 else None

    status = "healthy"
    if ratio is not None and ratio < 0.6:
        status = "degraded"
    if ratio is not None and ratio < 0.3:
        status = "critical"

    return {
        "enabled": True,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sample_size": len(samples),
        "total_urls_found": len(results),
        "reachable_count": len(reachable),
        "unreachable_count": len(unreachable),
        "skipped_count": len(skipped),
        "reachability_ratio": ratio,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
        "results": results,
        "status": status,
    }
