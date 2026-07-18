"""东方财富股吧采集器，支持25个板块，带反检测和重试机制。"""
import os
import re
import html as html_mod
import requests
import time
from datetime import datetime
from typing import List, Dict, Optional

from .anti_detection import get_anti_detection

SECTORS = {
    "nasdaq":        {"name": "纳斯达克", "code": "of159941", "etf": "513100"},
    "gold":          {"name": "黄金",     "code": "of518880", "etf": "518880"},
    "cpo":           {"name": "CPO通信",  "code": "of515880", "etf": "515880"},
    "semiconductor": {"name": "半导体",   "code": "of512480", "etf": "512480"},
    "bank":          {"name": "银行",     "code": "of512800", "etf": "512800"},
    "securities":    {"name": "证券",     "code": "of512000", "etf": "512000"},
    "biotech":       {"name": "创新药",   "code": "of159992", "etf": "159992"},
    "consumer":      {"name": "消费",     "code": "of510150", "etf": "510150"},
    "newenergy":     {"name": "新能源",   "code": "of516160", "etf": "516160"},
    "insurance":      {"name": "保险",   "code": "of512570", "etf": "512570"},
    "baijiu":         {"name": "白酒",   "code": "of512690", "etf": "512690"},
    "food":           {"name": "食品",   "code": "of515080", "etf": "515080"},
    "medicine":       {"name": "医药",   "code": "of512010", "etf": "512010"},
    "appliance":      {"name": "家电",   "code": "of159996", "etf": "159996"},
    "tourism":        {"name": "文旅",   "code": "of159766", "etf": "159766"},
    "electronics":    {"name": "电子",   "code": "of159997", "etf": "159997"},
    "computer":       {"name": "计算机", "code": "of512720", "etf": "512720"},
    "communication":  {"name": "通信",   "code": "of515050", "etf": "515050"},
    "media":          {"name": "传媒",   "code": "of512980", "etf": "512980"},
    "nonferrous":     {"name": "有色",   "code": "of512400", "etf": "512400"},
    "coal":           {"name": "煤炭",   "code": "of515220", "etf": "515220"},
    "chemical":       {"name": "化工",   "code": "of516220", "etf": "516220"},
    "steel":          {"name": "钢铁",   "code": "of515210", "etf": "515210"},
    "realestate":     {"name": "地产",   "code": "of512200", "etf": "512200"},
    "infrastructure": {"name": "基建",   "code": "of516950", "etf": "516950"},
}

_PROXY_URL = os.environ.get("MOM_INDEX_PROXY_URL", "http://127.0.0.1:7890")
PROXY = {"http": _PROXY_URL, "https": _PROXY_URL} if os.environ.get("MOM_INDEX_PROXY", "") == "1" else None

MAX_RETRIES = 3
RETRY_DELAY_BASE = 2
REQUEST_TIMEOUT = 20

_ad = get_anti_detection()


def _retry_fetch(url: str, headers: Dict, max_retries: int = MAX_RETRIES) -> Optional[str]:
    """带重试机制的 HTTP 请求，失败返回 None。"""
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            resp = requests.get(
                url, 
                headers=headers, 
                proxies=PROXY, 
                timeout=REQUEST_TIMEOUT
            )
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            
            if not resp.text or len(resp.text) < 100:
                raise ValueError("响应内容过短，可能被风控拦截")
            
            return resp.text
            
        except requests.exceptions.Timeout as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = RETRY_DELAY_BASE * (attempt + 1)
                print(f"    [股吧] 请求超时（第{attempt + 1}次），{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"    [股吧] 请求超时（已重试{max_retries}次）: {url}")
                
        except requests.exceptions.ConnectionError as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = RETRY_DELAY_BASE * (attempt + 1)
                print(f"    [股吧] 连接失败（第{attempt + 1}次），{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"    [股吧] 连接失败（已重试{max_retries}次）: {e}")
                
        except requests.exceptions.HTTPError as e:
            last_exception = e
            if 400 <= resp.status_code < 500 and attempt < max_retries:
                print(f"    [股吧] HTTP {resp.status_code} 错误，跳过重试")
                break
            if attempt < max_retries:
                wait_time = RETRY_DELAY_BASE * (attempt + 1)
                print(f"    [股吧] HTTP错误 {resp.status_code}（第{attempt + 1}次），{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"    [股吧] HTTP错误（已重试{max_retries}次）: {e}")
                
        except (requests.exceptions.RequestException, ValueError) as e:
            last_exception = e
            if attempt < max_retries:
                wait_time = RETRY_DELAY_BASE * (attempt + 1)
                print(f"    [股吧] 请求异常（第{attempt + 1}次），{wait_time}秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"    [股吧] 请求失败（已重试{max_retries}次）: {e}")
    
    return None


def fetch_board(code: str) -> str:
    """获取股吧页面 HTML，使用反检测请求头和重试机制。"""
    url = f"https://guba.eastmoney.com/list,{code}.html"
    headers = _ad.get_common_headers(referer="https://guba.eastmoney.com")
    
    result = _retry_fetch(url, headers)
    if result is None:
        raise RuntimeError(f"获取股吧页面失败: {code}")
    
    return result


def parse_posts(html_content: str) -> List[Dict]:
    """解析帖子列表，优先行级匹配保证字段对齐，失败则兜底全局匹配。"""
    title_pattern = re.compile(
        r'<a[^>]*href="(/news,[^"]*)"[^>]*title="([^"]*)"[^>]*>',
        re.DOTALL
    )

    row_pattern = re.compile(
        r'<div[^>]*class="[^"]*articleh[^"]*"[^>]*>(.*?)</div>',
        re.DOTALL
    )

    titles = title_pattern.findall(html_content)
    rows = row_pattern.findall(html_content)

    if rows and len(rows) > 0:
        return _parse_posts_by_rows(rows)

    read_pattern = re.compile(r'<cite[^>]*class="[^"]*l1[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)
    reply_pattern = re.compile(r'<cite[^>]*class="[^"]*l2[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)
    author_pattern = re.compile(r'<cite[^>]*class="[^"]*l4[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', re.DOTALL)
    date_pattern = re.compile(r'<cite[^>]*class="[^"]*l5[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)

    reads = read_pattern.findall(html_content)
    replies = reply_pattern.findall(html_content)
    authors = author_pattern.findall(html_content)
    dates = date_pattern.findall(html_content)

    field_lists = [titles, reads, replies, authors, dates]
    lengths = [len(lst) for lst in field_lists]
    min_len = min(lengths)
    max_len = max(lengths)
    if max_len > 0 and max_len - min_len > max_len * 0.1:  # 差异超过10%
        print(f"  [股吧解析警告] 字段长度不一致: titles={len(titles)}, reads={len(reads)}, "
              f"replies={len(replies)}, authors={len(authors)}, dates={len(dates)}")

    posts = []
    count = min(len(titles), min_len) if max_len > 0 else len(titles)
    for i in range(count):
        url, title = titles[i]
        title = html_mod.unescape(title.strip())
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'[\x00-\x1f\x7f]', '', title).strip()
        if not title or title == '点击开始搜索':
            continue

        def safe_get(lst, idx, default=""):
            return lst[idx].strip() if idx < len(lst) else default

        author = html_mod.unescape(safe_get(authors, i, "未知"))
        author = re.sub(r'<[^>]+>', '', author)

        post_id = _extract_post_id(url)
        if not post_id:
            continue

        posts.append({
            "id": f"guba_{post_id}",
            "title": title,
            "url": f"https://guba.eastmoney.com{url}",
            "platform": "guba",
            "author": author,
            "reads": safe_get(reads, i, "0"),
            "replies": safe_get(replies, i, "0"),
            "date": safe_get(dates, i, "未知"),
            "collected_at": datetime.now().isoformat(),
        })
    return posts


def _extract_post_id(url: str) -> Optional[str]:
    """从股吧 URL 中安全提取帖子 ID。"""
    try:
        parts = url.split(',')
        if len(parts) >= 2:
            return parts[-1].replace('.html', '')
    except Exception:
        pass
    return None


def _parse_posts_by_rows(rows: List[str]) -> List[Dict]:
    """按行解析帖子，确保字段对齐。"""
    title_pat = re.compile(r'<a[^>]*href="(/news,[^"]*)"[^>]*title="([^"]*)"[^>]*>', re.DOTALL)
    read_pat = re.compile(r'<cite[^>]*class="[^"]*l1[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)
    reply_pat = re.compile(r'<cite[^>]*class="[^"]*l2[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)
    author_pat = re.compile(r'<cite[^>]*class="[^"]*l4[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>', re.DOTALL)
    date_pat = re.compile(r'<cite[^>]*class="[^"]*l5[^"]*"[^>]*>(.*?)</cite>', re.DOTALL)

    posts = []
    now = datetime.now().isoformat()
    for row in rows:
        title_match = title_pat.search(row)
        if not title_match:
            continue
        url, title = title_match.groups()

        title = html_mod.unescape(title.strip())
        title = re.sub(r'<[^>]+>', '', title)
        title = re.sub(r'[\x00-\x1f\x7f]', '', title).strip()
        if not title or title == '点击开始搜索':
            continue

        post_id = _extract_post_id(url)
        if not post_id:
            continue

        def safe_search(pat, text, default=""):
            m = pat.search(text)
            return m.group(1).strip() if m else default

        author = html_mod.unescape(safe_search(author_pat, row, "未知"))
        author = re.sub(r'<[^>]+>', '', author)

        posts.append({
            "id": f"guba_{post_id}",
            "title": title,
            "url": f"https://guba.eastmoney.com{url}",
            "platform": "guba",
            "author": author,
            "reads": safe_search(read_pat, row, "0"),
            "replies": safe_search(reply_pat, row, "0"),
            "date": safe_search(date_pat, row, "未知"),
            "collected_at": now,
        })
    return posts


def collect_all() -> Dict[str, List[Dict]]:
    """采集所有板块帖子，带人类延迟防风控。"""
    result = {}
    for sector_key, cfg in SECTORS.items():
        try:
            html = fetch_board(cfg["code"])
            posts = parse_posts(html)
            result[sector_key] = posts
            print(f"  [{cfg['name']}] 采集到 {len(posts)} 条帖子")
            # 板块之间加延迟
            _ad.sleep_like_human("scroll")
        except Exception as e:
            print(f"  [{cfg['name']}] 采集失败: {e}")
            result[sector_key] = []
    return result


if __name__ == "__main__":
    data = collect_all()
    for k, v in data.items():
        print(f"{k}: {len(v)} posts")
