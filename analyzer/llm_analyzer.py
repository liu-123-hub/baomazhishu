"""宝妈指数 LLM 分析引擎，多维度分类与判定。"""
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json

@dataclass
class Signal:
    """单个判定信号。"""
    name: str
    weight: float
    description: str

NEWBIE_SIGNALS = [
    Signal("身份自述", 8, "明确自称小白/新手/刚入门/宝妈"),
    Signal("知识求助", 6, "在问基础问题（怎么买/在哪看/什么意思）"),
    Signal("决策依赖", 7, "请求他人替自己做投资决策（该不该/要不要/能不能）"),
    Signal("情绪恐慌", 5, "表达明显的恐惧/焦虑/后悔情绪"),
    Signal("跟风行为", 6, "提及跟别人买/听说/博主推荐/朋友说"),
    Signal("过度乐观", 4, "非理性乐观（梭哈/稳赚/必涨/躺赚）"),
    Signal("短期思维", 3, "关注明天/后天/今天涨跌，非长期视角"),
    Signal("金额极小", 2, "讨论几百几千块的投资，试水心态"),
    Signal("术语缺失", 4, "全文无任何专业术语（PE/PB/溢价率等）"),
    Signal("互动异常", 3, "大量emoji/感叹号/问号，情绪化表达"),
    Signal("市场异动", 6, "新闻/讨论提及极端涨跌或罕见波动，易引发散户情绪"),
]

PRO_SIGNALS = [
    Signal("专业术语", -5, "使用PE/PB/ROE/基本面/技术面/估值等专业词汇"),
    Signal("策略思维", -4, "讨论定投/仓位/分散/对冲/止损等策略"),
    Signal("数据引用", -4, "引用具体财报数据/宏观指标/研报观点"),
    Signal("风险意识", -3, "明确提及风险/仅供参考/不构成建议"),
    Signal("长期视角", -3, "讨论长期趋势/定投计划/年度收益"),
    Signal("冷静表达", -2, "理性分析，客观陈述，无情绪化表达"),
]

NEWS_EXTREME_KEYWORDS = {
    "暴涨": ["涨停", "暴涨", "飙升", "大涨", "猛拉", "逆市", "爆拉", "疯涨", "涨停潮", "拉升", "狂涨", "猛涨", "连涨", "创新高", "新高", "旱地拔葱", "起飞"],
    "暴跌": ["暴跌", "跳水", "大跌", "崩了", "闪崩", "腰斩", "重挫", "狂泻", "跌超", "暴跌", "断崖", "跳水", "杀跌", "大跌眼镜", "破位", "新低", "翻车"],
    "情绪渲染": ["过山车", "吵翻了", "炸锅", "慌了", "疯了", "惊呆", "罕见", "暴力", "异常", "诡异", "意外", "突然", "崩了", "凉了", "彻底慌了", "巨震", "巨量", "天量", "地量"],
    "资金异动": ["吸金", "爆买", "抢筹", "跑路", "出逃", "大举买入", "疯狂涌入", "资金追捧", "越涨越买", "资金流入", "资金流出", "逆势流入"],
    "散户热议": ["基民", "网友", "股民", "散户", "吵翻", "吵起来", "看呆", "看懵", "懵了", "亏哭", "赚翻", "嗨了", "沸腾"],
}

NEWBIE_KEYWORDS = {
    "身份自述": ["小白", "新手", "新人", "刚入", "第一次", "菜鸟", "萌新", "宝妈", "全职妈妈", "学生党", "基民", "散户"],
    "知识求助": ["不懂", "请教", "各位大哥", "大佬", "请问", "有没有人", "谁知道", "求助", "怎么买", "在哪看", "什么意思", "怎么看", "为什么"],
    "决策依赖": ["该不该", "要不要", "能不能", "可以吗", "行不行", "靠谱吗", "还能上车吗", "现在入手", "还会涨吗", "还会跌吗", "还能买吗", "可以买吗", "能买吗", "能入吗"],
    "情绪恐慌": ["好慌", "救命", "完了", "哭了", "怕了", "吓死", "心态崩", "太惨", "亏死了", "割肉", "后悔", "早知道", "亏麻了", "跌麻了", "血亏", "亏惨了", "深套", "套牢", "慌了", "崩了", "暴跌", "崩盘", "亏哭"],
    "跟风行为": ["跟着买的", "别人推荐", "博主说", "听说", "朋友说", "同事买", "群里说", "都在买", "大家都", "网友说"],
    "过度乐观": ["冲", "梭哈", "稳赚", "必涨", "躺赚", "满仓干", "起飞", "暴富", "暴力", "疯涨", "涨停潮", "赚翻", "嗨了", "沸腾"],
    "短期思维": ["明天涨", "今天跌", "后天走势", "今天买", "今日", "盘中", "短线"],
}

PRO_KEYWORDS = {
    "专业术语": ["PE", "PB", "ROE", "溢价率", "折价", "估值", "基本面", "技术面", "MACD", "KDJ"],
    "策略思维": ["定投", "仓位", "分散", "对冲", "止损", "止盈", "网格", "轮动", "资产配置"],
    "数据引用": ["季报", "年报", "GDP", "CPI", "非农", "美联储", "加息", "降息", "收益率", "年化", "研报"],
    "风险意识": ["仅供参考", "不构成建议", "个人观点", "理性投资", "风险自担", "谨慎"],
    "长期视角": ["长期持有", "定投计划", "年度", "养老", "十年", "长期"],
    "冷静表达": ["分析", "观点", "看法", "逻辑", "原因在于", "机构认为"],
}

BUY_KEYWORDS = [
    "上车", "冲", "梭哈", "all in", "满仓", "抄底", "加仓", "买入", "买了", "入手", "已入",
    "追", "杀入", "建仓", "补仓", "定投", "已上车",
    "还能买吗", "还能上车吗", "可以买吗", "能不能买", "要不要入",
    "想买", "想入", "心动", "看着眼馋", "忍不住",
    "后悔没买", "错过", "买少了", "早知道就买了", "再不买",
    "涨停", "暴涨", "飙升", "大涨", "拉升", "疯涨", "连涨", "创新高", "吸金", "爆买", "抢筹",
]

SELL_KEYWORDS = [
    "割肉", "割", "止损", "清仓", "减仓", "出货", "卖了", "出了", "跑了", "走人",
    "不玩了", "离场", "下车", "赎回",
    "要不要割", "要不要走", "该不该卖", "还能留吗", "要不要清",
    "想卖", "想走", "想割", "想跑",
    "亏了", "亏麻了", "亏惨了", "深套", "套牢", "后悔买了", "被套",
    "跌麻了", "跌惨了", "血亏", "亏死", "跌死", "跌崩",
    "暴跌", "跳水", "大跌", "闪崩", "腰斩", "重挫", "狂泻", "跌超", "杀跌", "跑路", "出逃",
]


@dataclass
class AnalysisResult:
    """单条帖子的分析结果。"""
    post_id: str
    title: str
    platform: str
    sector: str
    
    newbie_score: float = 0.0
    newbie_confidence: str = "low"
    
    matched_newbie: List[Tuple[str, str, float]] = field(default_factory=list)  
    matched_pro: List[Tuple[str, str, float]] = field(default_factory=list)
    
    level: str = "未判定"
    reasoning: str = ""
    sentiment_score: float = 0
    intent: str = "neutral"
    intent_strength: float = 0
    
    key_signals: List[str] = field(default_factory=list)


def analyze_post(post: Dict, sector: str) -> AnalysisResult:
    title = post.get("title", "")
    content = post.get("content", "")
    full_text = f"{title} {content}" if content else title
    
    SPAM_PATTERNS = [
        "我是冲着金条来的",
        "金条来的，你呢",
        "领金条",
        "签到",
        "打卡",
        "广告",
    ]
    for spam in SPAM_PATTERNS:
        if spam in full_text:
            result = AnalysisResult(
                post_id=post.get("id", ""),
                title=title[:80],
                platform=post.get("platform", "unknown"),
                sector=sector,
                newbie_score=0,
                newbie_confidence="high",
                level="垃圾帖",
                reasoning=f"检测到垃圾/活动帖（命中: 「{spam}」），已过滤，不计入指数。",
            )
            return result
    
    result = AnalysisResult(
        post_id=post.get("id", ""),
        title=title[:80],
        platform=post.get("platform", "unknown"),
        sector=sector,
    )
    
    matched_newbie = []
    matched_pro = []
    matched_news_extreme = []
    
    for signal in NEWBIE_SIGNALS:
        if signal.name == "市场异动":
            extreme_kws = []
            for cat, kws in NEWS_EXTREME_KEYWORDS.items():
                hit = [kw for kw in kws if kw in full_text]
                if hit:
                    extreme_kws.extend(hit)
            if extreme_kws:
                matched_newbie.append((signal.name, signal.description, signal.weight, extreme_kws))
                matched_news_extreme = extreme_kws
            continue
        keywords = NEWBIE_KEYWORDS.get(signal.name, [])
        matched_kws = [kw for kw in keywords if kw.lower() in full_text.lower()]
        if matched_kws:
            matched_newbie.append((signal.name, signal.description, signal.weight, matched_kws))
    
    for signal in PRO_SIGNALS:
        keywords = PRO_KEYWORDS.get(signal.name, [])
        matched_kws = [kw for kw in keywords if kw.lower() in full_text.lower()]
        if matched_kws:
            matched_pro.append((signal.name, signal.description, signal.weight, matched_kws))
    
    extra_score = 0
    extra_reasons = []
    
    if len(title) < 12 and any(kw in title for kw in ["涨", "跌", "买", "卖"]):
        extra_score += 3
        extra_reasons.append("标题极短+情绪化，典型小白特征")
    
    if title.endswith("吗") or title.endswith("呢") or title.endswith("？"):
        extra_score += 2
        extra_reasons.append("以问句结尾，在寻求答案")
    
    exclaim_count = title.count("！") + title.count("!")
    if exclaim_count >= 1:
        extra_score += exclaim_count * 2
        extra_reasons.append(f"标题含{exclaim_count}个感叹号，情绪强烈")
    
    if matched_news_extreme:
        extra_score += len(set(matched_news_extreme))
        extra_reasons.append(f"含市场异动词汇({', '.join(list(set(matched_news_extreme))[:3])})，易引发散户跟风")
    
    total_newbie = sum(s[2] for s in matched_newbie) + extra_score
    total_pro = abs(sum(s[2] for s in matched_pro))
    
    is_news_platform = post.get("platform", "") in ("guba", "google_news", "netease", "eastmoney", "sina", "tonghuashun")
    pro_penalty = total_pro * (0.4 if is_news_platform else 0.8)
    
    raw_score = total_newbie - pro_penalty
    result.newbie_score = max(0, min(100, raw_score * 4 + 10))
    
    total_signals = len(matched_newbie) + len(matched_pro)
    if total_signals >= 4:
        result.newbie_confidence = "high"
    elif total_signals >= 2:
        result.newbie_confidence = "medium"
    else:
        result.newbie_confidence = "low"
    
    s = result.newbie_score
    if s >= 50:
        result.level = "纯小白"
    elif s >= 35:
        result.level = "偏小白"
    elif s >= 20:
        result.level = "中间派"
    elif s >= 10:
        result.level = "偏专业"
    else:
        result.level = "专业投资者"
    
    result.reasoning = _generate_reasoning(
        title, matched_newbie, matched_pro, extra_reasons,
        total_newbie, total_pro, result
    )
    
    result.sentiment_score = _analyze_sentiment(full_text)
    
    buy_count = sum(1 for kw in BUY_KEYWORDS if kw in full_text)
    sell_count = sum(1 for kw in SELL_KEYWORDS if kw in full_text)
    
    if buy_count > sell_count:
        result.intent = "buy"
        result.intent_strength = min(1.0, buy_count / 5)
    elif sell_count > buy_count:
        result.intent = "sell"
        result.intent_strength = min(1.0, sell_count / 5)
    else:
        result.intent = "neutral"
        result.intent_strength = 0
    
    result.key_signals = []
    for name, desc, weight, kws in matched_newbie[:3]:
        result.key_signals.append(f"「{name}」{desc} (命中: {', '.join(kws[:2])})")
    for name, desc, weight, kws in matched_pro[:2]:
        result.key_signals.append(f"「{name}」{desc} (命中: {', '.join(kws[:2])})")
    
    result.matched_newbie = [(n, d, w) for n, d, w, _ in matched_newbie]
    result.matched_pro = [(n, d, w) for n, d, w, _ in matched_pro]
    
    return result


def _generate_reasoning(
    title: str,
    matched_newbie: List[Tuple],
    matched_pro: List[Tuple],
    extra_reasons: List[str],
    total_newbie: float,
    total_pro: float,
    result: AnalysisResult,
) -> str:
    parts = []
    
    parts.append(f"帖子「{title[:40]}...」")
    
    if not matched_newbie and not matched_pro:
        parts.append("未命中明确的信号词，内容较短或信息不足。")
        parts.append("根据有限信息判定为中间派。")
        return " ".join(parts)
    
    if matched_newbie:
        signal_descs = [f"{name}({weight}分)" for name, desc, weight, kws in matched_newbie]
        parts.append(f"命中{len(matched_newbie)}个小信号: {', '.join(signal_descs)}。")
    
    if matched_pro:
        signal_descs = [f"{name}({weight}分)" for name, desc, weight, kws in matched_pro]
        parts.append(f"命中{len(matched_pro)}个专业信号: {', '.join(signal_descs)}。")
    
    if extra_reasons:
        parts.extend(extra_reasons)
    
    parts.append(f"综合得分{result.newbie_score}分，")
    parts.append(f"判定为「{result.level}」")
    parts.append(f"(置信度: {result.newbie_confidence})。")
    
    return " ".join(parts)


def _analyze_sentiment(text: str) -> float:
    greed_words = [
        "冲", "梭哈", "稳赚", "必涨", "躺赚", "满仓", "抄底", "起飞", "暴涨", "翻倍", "赚了", "盈利",
        "涨停", "飙升", "大涨", "拉升", "疯涨", "连涨", "创新高", "吸金", "爆买", "抢筹", "逆市",
        "涨停潮", "嗨了", "沸腾", "赚翻", "涨超",
    ]
    fear_words = [
        "割肉", "止损", "亏", "跌惨", "暴跌", "崩盘", "完了", "套牢", "深套", "亏了", "赔了", "大跌",
        "跳水", "闪崩", "腰斩", "重挫", "狂泻", "跌超", "杀跌", "跑路", "出逃", "亏麻了", "跌麻了",
        "血亏", "亏惨了", "崩了", "凉了", "慌了", "翻车",
    ]
    
    greed = sum(1 for w in greed_words if w in text)
    fear = sum(1 for w in fear_words if w in text)
    
    total = greed + fear
    if total == 0:
        return 0.0
    return round((greed - fear) / total, 2)


def analyze_sector(posts: List[Dict], sector: str) -> List[AnalysisResult]:
    results = []
    for post in posts:
        result = analyze_post(post, sector)
        results.append(result)
    
    results.sort(key=lambda r: r.newbie_score, reverse=True)
    return results


def analyze_all(sector_data: Dict[str, List[Dict]]) -> Dict[str, List[AnalysisResult]]:
    all_results = {}
    for sector, posts in sector_data.items():
        print(f"  分析 {sector}: {len(posts)} 条帖子...")
        all_results[sector] = analyze_sector(posts, sector)
    return all_results
