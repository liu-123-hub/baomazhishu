
GUBA = "东方财富股吧"
XHS = "小红书"
XUEQIU_COMMUNITY = "雪球社区"
GOOGLE_NEWS = "Google News"
NETEASE = "网易财经"
EASTMONEY_NEWS = "东方财富资讯"
THS = "同花顺财经"
MARKET_DATA = "行情数据(AKShare)"
CAPITAL_FLOW = "市场异动数据(AKShare)"

PROBE_CONFIG = {
    GUBA: {
        "method": "http_head",
        "url": "https://guba.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    XHS: {
        "method": "env_key",
        "env_key": "RNODE_API_KEY",
        "fallback_url": "https://rnote.dev/",
        "timeout": 3.0,
    },
    XUEQIU_COMMUNITY: {
        "method": "http_head",
        "url": "https://xueqiu.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302, 403),
    },
    GOOGLE_NEWS: {
        "method": "http_head",
        "url": "https://news.google.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    NETEASE: {
        "method": "http_head",
        "url": "https://finance.163.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    EASTMONEY_NEWS: {
        "method": "http_head",
        "url": "https://finance.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    THS: {
        "method": "http_head",
        "url": "https://news.10jqka.com.cn/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    MARKET_DATA: {
        "method": "http_head",
        "url": "https://finance.sina.com.cn/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302),
    },
    CAPITAL_FLOW: {
        "method": "http_head",
        "url": "https://push2.eastmoney.com/",
        "timeout": 3.0,
        "expected_status": (200, 301, 302, 404),
    },
}
