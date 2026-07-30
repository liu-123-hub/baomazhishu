"""宝妈指数计算引擎，各板块独立计算并维护历史曲线。

板块分类体系 v2.0（2026-07-30 重构）:
- 两大维度：投资风格维度（4大梯队成长赛道 + 价值防御） + 板块属性维度（标准行业 vs 跨行业概念）
- 双重归属：每条帖子可同时归入最多3个板块（1个主行业 + 最多2个概念赛道）
- 上下游产业链：每个板块在SECTOR_META中标记产业链位置
"""
from datetime import datetime, date
from typing import Dict, List, Optional
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ============================================================
# 板块代码 → 中文显示名称（唯一真值来源，所有其他文件从此处导入）
# ============================================================
SECTOR_NAMES = {
    # ── 第一梯队 T1：AI算力硬科技（市场最强主线，弹性最大）──
    "semiconductor": "半导体",
    "electronics": "电子",
    "ai_computing": "AI算力",
    "cpo": "CPO光通信",
    # ── 第二梯队 T2：高端制造/智能科技（产业升级β）──
    "computer": "计算机",
    "communication": "通信",
    "military": "军工",
    "robot": "机器人",
    # ── 第三梯队 T3：新能源/电力设备（产业趋势β）──
    "newenergy": "新能源",
    "battery": "电池",
    "power_grid": "电力设备",
    # ── 第四梯队 T4：消费医疗/文化传媒（稳健成长）──
    "medicine": "医药",
    "baijiu": "白酒",
    "food": "食品饮料",
    "appliance": "家电",
    "tourism": "文旅",
    "media": "传媒",
    "biotech": "创新药",
    "consumer": "大消费",
    # ── 价值防御板块：大金融 ──
    "bank": "银行",
    "securities": "券商",
    "insurance": "保险",
    # ── 价值防御板块：周期资源 ──
    "coal": "煤炭",
    "crude_oil": "石油石化",
    "nonferrous": "有色金属",
    "chemical": "化工",
    "steel": "钢铁",
    # ── 价值防御板块：基建地产 ──
    "infrastructure": "基建",
    "realestate": "房地产",
    # ── 防御资产/海外 ──
    "gold": "黄金",
    "nasdaq": "纳斯达克",
}

# ============================================================
# 板块元数据：属性界定 + 梯队归属 + 产业链位置 + 关联行业
# sector_type: "industry" = 证监会标准行业板块, "concept" = 跨行业概念赛道
# tier: "T1"~"T4" 成长梯队, "V1"~"V3" 价值防御层, "DEF" 防御资产
# ============================================================
SECTOR_META = {
    # ──── T1 第一梯队：AI算力硬科技 ────
    "semiconductor": {
        "sector_type": "industry",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "上游（芯片设计/制造/封测/设备/材料）",
        "csrc_category": "电子-半导体",
        "related_concepts": ["ai_computing", "cpo"],
    },
    "electronics": {
        "sector_type": "industry",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "中上游（消费电子/PCB/被动元件/光学/面板）",
        "csrc_category": "电子",
        "related_concepts": ["ai_computing", "cpo", "robot", "consumer"],
    },
    "ai_computing": {
        "sector_type": "concept",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "跨行业概念（GPU/服务器/IDC/液冷/HBM/算力调度）",
        "csrc_category": None,
        "spans_industries": ["电子", "计算机", "通信"],
        "related_industries": ["semiconductor", "electronics", "computer", "communication"],
    },
    "cpo": {
        "sector_type": "concept",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "跨行业概念（光模块/光芯片/CPO/光通信设备）",
        "csrc_category": None,
        "spans_industries": ["电子", "通信"],
        "related_industries": ["electronics", "communication", "semiconductor"],
    },

    # ──── T2 第二梯队：高端制造/智能科技 ────
    "computer": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中游（软件/信创/云计算/网络安全/AI应用）",
        "csrc_category": "计算机",
        "related_concepts": ["ai_computing", "robot"],
    },
    "communication": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中上游（运营商/通信设备/光纤光缆/卫星通信）",
        "csrc_category": "通信",
        "related_concepts": ["cpo", "ai_computing"],
    },
    "military": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中下游（航空航天/军工电子/舰船/兵器/军工材料）",
        "csrc_category": "国防军工",
        "related_concepts": [],
    },
    "robot": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（人形机器人/工业机器人/减速器/伺服电机/传感器）",
        "csrc_category": None,
        "spans_industries": ["机械", "电子", "计算机", "汽车"],
        "related_industries": ["electronics", "computer", "military"],
    },

    # ──── T3 第三梯队：新能源/电力设备 ────
    "newenergy": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "中下游（光伏/风电/新能源车/氢能/储能系统）",
        "csrc_category": "电力设备-新能源",
        "related_concepts": [],
    },
    "battery": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "中上游（锂电池/动力电池/储能电池/正负极/电解液/隔膜）",
        "csrc_category": "电力设备-电池",
        "related_concepts": ["newenergy"],
    },
    "power_grid": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "上游（特高压/智能电网/输变电/配网/电力信息化）",
        "csrc_category": "电力设备-电网",
        "related_concepts": [],
    },

    # ──── T4 第四梯队：消费医疗/文化传媒 ────
    "medicine": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "全链条（化药/中药/医疗器械/医疗服务/医药流通）",
        "csrc_category": "医药生物",
        "related_concepts": ["biotech"],
    },
    "baijiu": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "中上游（高端白酒/次高端白酒/区域白酒）",
        "csrc_category": "食品饮料-白酒",
        "related_concepts": ["consumer"],
    },
    "food": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "中游（调味品/乳制品/休闲食品/啤酒/饮料）",
        "csrc_category": "食品饮料-食品",
        "related_concepts": ["consumer"],
    },
    "appliance": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（白色家电/小家电/厨电/智能家居）",
        "csrc_category": "家用电器",
        "related_concepts": ["consumer"],
    },
    "tourism": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（旅游/酒店/免税/景区/餐饮/航空）",
        "csrc_category": "社会服务",
        "related_concepts": ["consumer"],
    },
    "media": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（游戏/影视/广告/出版/直播/AI应用）",
        "csrc_category": "传媒",
        "related_concepts": [],
    },
    "biotech": {
        "sector_type": "concept",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "跨行业概念（创新药研发/CXO/生物医药/基因治疗）",
        "csrc_category": None,
        "spans_industries": ["医药生物"],
        "related_industries": ["medicine"],
    },
    "consumer": {
        "sector_type": "concept",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "跨行业概念（必选消费+可选消费，跨白酒/食品/家电/文旅/零售）",
        "csrc_category": None,
        "spans_industries": ["食品饮料", "家用电器", "社会服务", "商贸零售"],
        "related_industries": ["baijiu", "food", "appliance", "tourism"],
    },

    # ──── V1 价值防御：大金融 ────
    "bank": {
        "sector_type": "industry",
        "tier": "V1",
        "tier_name": "大金融（价值防御）",
        "chain_position": "全链条（国有大行/股份行/城商行/农商行）",
        "csrc_category": "银行",
        "related_concepts": [],
    },
    "securities": {
        "sector_type": "industry",
        "tier": "V1",
        "tier_name": "大金融（价值防御）",
        "chain_position": "全链条（券商/投行/资管/经纪业务）",
        "csrc_category": "非银金融-证券",
        "related_concepts": [],
    },
    "insurance": {
        "sector_type": "industry",
        "tier": "V1",
        "tier_name": "大金融（价值防御）",
        "chain_position": "全链条（寿险/财险/保险经纪/再保险）",
        "csrc_category": "非银金融-保险",
        "related_concepts": [],
    },

    # ──── V2 价值防御：周期资源 ────
    "coal": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "上游（动力煤/焦煤/煤炭开采/煤化工）",
        "csrc_category": "煤炭",
        "related_concepts": [],
    },
    "crude_oil": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "上游-中游（原油开采/油气服务/炼化/销售）",
        "csrc_category": "石油石化",
        "related_concepts": [],
    },
    "nonferrous": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "上游（铜/铝/锌/锂/稀土/黄金-工业金属）",
        "csrc_category": "有色金属",
        "related_concepts": [],
    },
    "chemical": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "中游（基础化工/新材料/煤化工/化纤/农化）",
        "csrc_category": "基础化工",
        "related_concepts": [],
    },
    "steel": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "中游（普钢/特钢/铁矿石/钢材加工）",
        "csrc_category": "钢铁",
        "related_concepts": [],
    },

    # ──── V3 价值防御：基建地产 ────
    "infrastructure": {
        "sector_type": "industry",
        "tier": "V3",
        "tier_name": "基建地产（价值防御）",
        "chain_position": "中上游（建筑/建材/工程机械/铁路/港口）",
        "csrc_category": "建筑装饰/建筑材料",
        "related_concepts": [],
    },
    "realestate": {
        "sector_type": "industry",
        "tier": "V3",
        "tier_name": "基建地产（价值防御）",
        "chain_position": "下游（房地产开发/物业/家居/中介）",
        "csrc_category": "房地产",
        "related_concepts": [],
    },

    # ──── DEF 防御资产/海外 ────
    "gold": {
        "sector_type": "concept",
        "tier": "DEF",
        "tier_name": "防御资产",
        "chain_position": "避险资产（黄金现货/黄金股/黄金ETF/贵金属）",
        "csrc_category": None,
        "spans_industries": ["有色金属", "贵金属"],
        "related_industries": ["nonferrous"],
    },
    "nasdaq": {
        "sector_type": "concept",
        "tier": "DEF",
        "tier_name": "海外资产",
        "chain_position": "海外市场（纳斯达克100/美股科技巨头）",
        "csrc_category": None,
        "spans_industries": ["海外市场"],
        "related_industries": [],
    },
}

# ============================================================
# 分类体系（一级分类 → 板块列表），按投资风格组织
# ============================================================
SECTOR_CATEGORIES = [
    {
        "code": "T1",
        "name": "第一梯队·AI算力硬科技",
        "description": "AI算力产业链：半导体/电子为核心，CPO/AI算力为跨行业概念主线，市场最强弹性",
        "children": ["semiconductor", "electronics", "ai_computing", "cpo"],
    },
    {
        "code": "T2",
        "name": "第二梯队·高端制造/智能科技",
        "description": "产业升级方向：计算机/通信/军工为标准行业，机器人为跨行业概念赛道",
        "children": ["computer", "communication", "military", "robot"],
    },
    {
        "code": "T3",
        "name": "第三梯队·新能源/电力设备",
        "description": "清洁能源产业链：新能源整车/电池/电力设备上中下游全覆盖",
        "children": ["newenergy", "battery", "power_grid"],
    },
    {
        "code": "T4",
        "name": "第四梯队·消费医疗/文化传媒",
        "description": "稳健成长板块：医药/消费/家电/文旅/传媒为标准行业，创新药/大消费为跨行业概念",
        "children": ["medicine", "baijiu", "food", "appliance", "tourism", "media", "biotech", "consumer"],
    },
    {
        "code": "V1",
        "name": "价值防御·大金融",
        "description": "金融三剑客：银行/券商/保险，低估值高股息防御板块",
        "children": ["bank", "securities", "insurance"],
    },
    {
        "code": "V2",
        "name": "价值防御·周期资源",
        "description": "上游周期品：煤炭/石油/有色/化工/钢铁，通胀受益+高股息",
        "children": ["coal", "crude_oil", "nonferrous", "chemical", "steel"],
    },
    {
        "code": "V3",
        "name": "价值防御·基建地产",
        "description": "稳增长板块：基建/建材/工程机械/房地产，政策驱动型",
        "children": ["infrastructure", "realestate"],
    },
    {
        "code": "DEF",
        "name": "防御资产/海外",
        "description": "避险与海外配置：黄金为避险概念，纳斯达克为海外科技指数",
        "children": ["gold", "nasdaq"],
    },
]

# 板块属性类型
INDUSTRY_SECTORS = [code for code, meta in SECTOR_META.items() if meta["sector_type"] == "industry"]
CONCEPT_SECTORS = [code for code, meta in SECTOR_META.items() if meta["sector_type"] == "concept"]

# 梯队颜色（前端使用）
TIER_COLORS = {
    "T1": "#ef4444",  # 红色-最热
    "T2": "#f97316",  # 橙色-高景气
    "T3": "#22c55e",  # 绿色-成长
    "T4": "#3b82f6",  # 蓝色-稳健
    "V1": "#64748b",  # 灰色-防御
    "V2": "#78716c",  # 暖灰-周期
    "V3": "#a16207",  # 褐色-稳增长
    "DEF": "#eab308",  # 金色-避险
}


def get_sector_type(code: str) -> str:
    """获取板块属性类型：industry=标准行业, concept=跨行业概念"""
    return SECTOR_META.get(code, {}).get("sector_type", "industry")


def get_sector_tier(code: str) -> str:
    """获取板块所属梯队：T1~T4, V1~V3, DEF"""
    return SECTOR_META.get(code, {}).get("tier", "T4")


def get_related_sectors(code: str) -> List[str]:
    """获取关联板块（双重归属建议）"""
    meta = SECTOR_META.get(code, {})
    if meta.get("sector_type") == "concept":
        return meta.get("related_industries", [])
    else:
        return meta.get("related_concepts", [])


def _empty_details() -> Dict:
    return {
        "total_posts": 0,
        "valid_posts": 0,
        "spam_posts": 0,
        "newbie_posts": 0,
        "pure_newbie": 0,
        "newbie_ratio": 0.0,
        "avg_newbie_score": 0.0,
        "avg_sentiment": 0.0,
        "purity_signal": 0.0,
        "activity": 0.0,
        "mom_buy_index": 0.0,
        "mom_sell_index": 0.0,
        "buy_sell_ratio": 0.0,
        "buy_count": 0,
        "sell_count": 0,
    }


def compute_sector_index(analysis_results: List) -> Dict:
    """计算单个板块的宝妈指数(0-100)，四个维度加权计算。"""
    if not analysis_results:
        return {
            "index": 0,
            "interpretation": "无数据",
            "details": _empty_details(),
            "top_newbie_posts": [],
        }
    
    total = len(analysis_results)
    
    valid_posts = [r for r in analysis_results if r.level != "垃圾帖"]
    spam_count = total - len(valid_posts)
    
    newbie_posts = [r for r in analysis_results if r.newbie_score >= 20]
    pure_newbie = [r for r in analysis_results if r.newbie_score >= 50]
    newbie_count = len(newbie_posts)
    
    newbie_ratio = (newbie_count / len(valid_posts)) * 100 if valid_posts else 0
    
    avg_newbie_score = sum(r.newbie_score for r in newbie_posts) / max(newbie_count, 1)
    
    sentiments = [abs(r.sentiment_score) for r in newbie_posts]
    avg_sentiment = sum(sentiments) / max(len(sentiments), 1) * 100
    
    purity_signal = (len(pure_newbie) / max(newbie_count, 1)) * 100 if newbie_count > 0 else 0
    activity_signal = min(100, len(valid_posts) / 80 * 100)
    
    # 四维权重：小白占比40%(覆盖广度) + 平均小白分25%(个体烈度) + 情绪强度20%(情绪化程度) + 纯度信号15%(极端小白比例)
    index = (
        newbie_ratio * 0.40 +
        avg_newbie_score * 0.25 +
        avg_sentiment * 0.20 +
        purity_signal * 0.15
    )
    
    index = round(min(100, index), 1)
    
    newbie_buy = [r for r in newbie_posts if r.intent == "buy"]
    newbie_sell = [r for r in newbie_posts if r.intent == "sell"]
    
    buy_ratio = len(newbie_buy) / max(newbie_count, 1)
    sell_ratio = len(newbie_sell) / max(newbie_count, 1)
    buy_intensity = sum(r.intent_strength for r in newbie_buy) / max(len(newbie_buy), 1)
    sell_intensity = sum(r.intent_strength for r in newbie_sell) / max(len(newbie_sell), 1)
    
    # 买/卖指数权重：参与占比50% + 小白烈度修正30% + 关键词强度20%
    mom_buy_index = round(min(100, (
        buy_ratio * 100 * 0.50 +
        (avg_newbie_score / 100) * buy_ratio * 30 * 0.30 +
        buy_intensity * 100 * 0.20
    )), 1)
    
    mom_sell_index = round(min(100, (
        sell_ratio * 100 * 0.50 +
        (avg_newbie_score / 100) * sell_ratio * 30 * 0.30 +
        sell_intensity * 100 * 0.20
    )), 1)
    
    buy_sell_ratio = round(min(20, len(newbie_buy) / max(len(newbie_sell), 1)), 1)
    
    return {
        "index": index,
        "interpretation": interpret_index(index),
        "details": {
            "total_posts": total,
            "valid_posts": len(valid_posts),
            "spam_posts": spam_count,
            "newbie_posts": newbie_count,
            "pure_newbie": len(pure_newbie),
            "newbie_ratio": round(newbie_ratio, 1),
            "avg_newbie_score": round(avg_newbie_score, 1),
            "avg_sentiment": round(avg_sentiment, 1),
            "purity_signal": round(purity_signal, 1),
            "activity": round(activity_signal, 1),
            "mom_buy_index": mom_buy_index,
            "mom_sell_index": mom_sell_index,
            "buy_sell_ratio": buy_sell_ratio,
            "buy_count": len(newbie_buy),
            "sell_count": len(newbie_sell),
        },
        "top_newbie_posts": [
            {
                "title": r.title[:60],
                "score": r.newbie_score,
                "level": r.level,
                "reasoning": r.reasoning[:150],
                "sentiment": r.sentiment_score,
                "intent": r.intent,
                "intent_label": {"buy": "🟢 买入", "sell": "🔴 卖出", "neutral": "⚪ 观望"}.get(r.intent, ""),
                "key_signals": r.key_signals[:2],
            }
            for r in sorted(newbie_posts, key=lambda x: x.newbie_score, reverse=True)[:5]
        ],
    }


def interpret_index(index: float) -> str:
    """将指数数值映射为五级中文解读标签。"""
    if index >= 75:
        return "🔴 极度狂热 — 擦鞋童时刻！小白情绪爆表，历史级别的危险信号"
    elif index >= 60:
        return "🟠 高度警惕 — 小白大量涌入，市场情绪过热，建议大幅减仓"
    elif index >= 40:
        return "🟡 开始升温 — 小白活跃度明显上升，需保持关注"
    elif index >= 20:
        return "🟢 正常区间 — 小白参与度适中，无需特别操作"
    else:
        return "🔵 极度冷清 — 小白沉默不语，可能是市场底部信号"


def load_history() -> Dict:
    """读取历史指数记录，自动对同日期记录去重（保留时间戳最新者）。"""
    history_file = os.path.join(DATA_DIR, "history.json")
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = data.get("records", [])
        if len(records) > 0:
            seen = {}
            invalid_count = 0
            for record in records:
                date = record.get("date")
                if not date:
                    invalid_count += 1
                    continue
                if date in seen:
                    old_ts = seen[date].get("timestamp", "")
                    new_ts = record.get("timestamp", "")
                    if new_ts >= old_ts:
                        seen[date] = record
                else:
                    seen[date] = record
            deduped = sorted(seen.values(), key=lambda r: r["date"])
            changed = False
            if len(deduped) != len(records) - invalid_count:
                print(f"  [历史数据] 日期去重: {len(records)} → {len(deduped)} 条")
                changed = True
            if invalid_count > 0:
                print(f"  [历史数据] 跳过无 date 字段的记录: {invalid_count} 条")
                changed = True
            if changed:
                data["records"] = deduped
        return data
    return {"records": []}


def save_history(history: Dict):
    """原子写入历史记录到 JSON 文件（tmp + replace 避免写入中断损坏）。"""
    history_file = os.path.join(DATA_DIR, "history.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = history_file + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, history_file)


def add_record(sector_indices: Dict[str, Dict], analysis_results: Dict):
    """追加当日指数快照，同日重复执行会覆盖旧记录。"""
    history = load_history()
    
    record = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "sectors": sector_indices,
    }
    
    today = record["date"]
    existing = [r for r in history["records"] if r["date"] == today]
    if existing:
        history["records"] = [r for r in history["records"] if r["date"] != today]
    
    history["records"].append(record)
    history["records"].sort(key=lambda r: r["date"])
    save_history(history)


def _empty_sector_data() -> Dict:
    return {
        "index": 0,
        "interpretation": "无数据",
        "details": _empty_details(),
        "top_newbie_posts": [],
    }


def get_dashboard_data() -> Dict:
    """组装前端仪表盘所需结构：最新快照 + 各板块历史序列 + 记录数。"""
    history = load_history()
    records = history.get("records", [])

    latest = records[-1] if records else None

    sector_history = {code: [] for code in SECTOR_NAMES}

    for r in records:
        for sector, data in r.get("sectors", {}).items():
            if sector in sector_history:
                sector_history[sector].append({
                    "date": r["date"],
                    "index": data["index"],
                })

    if latest:
        sectors = latest.get("sectors", {})
        for sector in sector_history.keys():
            if sector not in sectors:
                sectors[sector] = _empty_sector_data()

    return {
        "latest": latest,
        "sector_history": sector_history,
        "record_count": len(records),
    }
