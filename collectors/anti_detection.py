"""反检测模块，提供浏览器指纹伪装、人类行为模拟、请求头轮换。"""
import random
import time
from typing import Dict, List, Optional
from datetime import datetime


class AntiDetection:
    """浏览器反检测，伪装成真人 Chrome。"""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]

    ACCEPT_HEADERS = [
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    ]

    ACCEPT_LANGUAGES = [
        "zh-CN,zh;q=0.9,en;q=0.8",
        "zh-CN,zh;q=0.9",
        "zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3",
    ]

    def __init__(self):
        self.request_count = 0
        self.last_ua = None
        self.session_start = datetime.now()

    def get_random_ua(self) -> str:
        ua = random.choice(self.USER_AGENTS)
        self.last_ua = ua
        return ua

    def get_common_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        ua = self.get_random_ua()
        headers = {
            "User-Agent": ua,
            "Accept": random.choice(self.ACCEPT_HEADERS),
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }

        if referer:
            headers["Referer"] = referer

        if "Chrome" in ua:
            version = ua.split("Chrome/")[1].split(".")[0]
            headers["sec-ch-ua"] = f'"Not_A Brand";v="8", "Chromium";v="{version}", "Google Chrome";v="{version}"'
            headers["sec-ch-ua-mobile"] = "?0"
            headers["sec-ch-ua-platform"] = '"Windows"'

        return headers

    def get_ajax_headers(self, referer: str) -> Dict[str, str]:
        return {
            "User-Agent": self.last_ua or self.get_random_ua(),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": random.choice(self.ACCEPT_LANGUAGES),
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": referer,
            "Origin": self._get_origin(referer),
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

    def human_delay(self, min_s: float = 0.5, max_s: float = 3.0) -> float:
        """模拟真人浏览延迟（高斯分布+周期性长停）。"""
        mean = (min_s + max_s) / 2
        std = (max_s - min_s) / 4
        delay = random.gauss(mean, std)
        delay = max(min_s, min(max_s, delay))

        self.request_count += 1

        if self.request_count % 10 == 0:
            delay += random.uniform(5, 15)

        if self.request_count % 50 == 0:
            delay += random.uniform(30, 60)

        if random.random() < 0.15:
            delay += random.uniform(2, 8)

        hour = datetime.now().hour
        if hour < 9 or hour > 18:
            delay *= random.uniform(1.2, 1.5)

        return delay

    def sleep_like_human(self, activity: str = "browsing") -> None:
        if activity == "search":
            delay = self.human_delay(2.0, 5.0)
        elif activity == "click":
            delay = self.human_delay(0.5, 2.0)
        elif activity == "scroll":
            delay = self.human_delay(1.0, 3.0)
        else:
            delay = self.human_delay(0.5, 3.0)

        time.sleep(delay)

    def get_playwright_launch_args(self) -> List[str]:
        return [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--no-first-run",
            "--disable-gpu",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-popup-blocking",
            "--disable-sync",
            "--no-default-browser-check",
            "--mute-audio",
        ]

    def get_stealth_scripts(self) -> List[str]:
        return [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            "window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};",
            """const q = navigator.permissions.query;
            navigator.permissions.query = (p) => p.name === 'notifications' ?
                Promise.resolve({state: Notification.permission}) : q(p);""",
            """Object.defineProperty(navigator, 'plugins', {get: () => [
                {name:'Chrome PDF Plugin', filename:'internal-pdf-viewer'},
                {name:'Chrome PDF Viewer', filename:'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                {name:'Native Client', filename:'internal-nacl-plugin'}
            ]});""",
            "Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN','zh','en-US','en']});",
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});",
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});",
            "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});",
        ]

    def inject_stealth(self, page) -> None:
        for script in self.get_stealth_scripts():
            page.add_init_script(script)

    def _get_origin(self, url: str) -> str:
        from urllib.parse import urlparse
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}"

    def should_rotate_session(self) -> bool:
        return self.request_count % 100 == 0


_ad_instance = None

def get_anti_detection() -> AntiDetection:
    global _ad_instance
    if _ad_instance is None:
        _ad_instance = AntiDetection()
    return _ad_instance
