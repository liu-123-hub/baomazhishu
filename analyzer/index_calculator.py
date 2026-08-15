from datetime import datetime, date
from typing import Dict, List, Optional
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

SECTOR_NAMES = {
    
    "semiconductor": "半导体",
    "electronics": "电子",
    "ai_computing": "AI算力",
    "cpo": "CPO光通信",
    "ai_application": "AI应用",
    "deepseek": "DeepSeek概念",
    
    "computer": "计算机",
    "communication": "通信",
    "military": "军工",
    "robot": "机器人",
    "humanoid_robot": "人形机器人",
    "ai_agent": "AI智能体",
    "low_altitude": "低空经济",
    "satellite_internet": "卫星互联网",
    
    "newenergy": "新能源",
    "battery": "电池",
    "power_grid": "电力设备",
    "solid_battery": "固态电池",
    "nuclear_fusion": "可控核聚变",
    
    "medicine": "医药",
    "baijiu": "白酒",
    "food": "食品饮料",
    "appliance": "家电",
    "tourism": "文旅",
    "media": "传媒",
    "biotech": "创新药",
    "consumer": "大消费",
    
    "bank": "银行",
    "securities": "券商",
    "insurance": "保险",
    
    "coal": "煤炭",
    "crude_oil": "石油石化",
    "nonferrous": "有色金属",
    "chemical": "化工",
    "steel": "钢铁",
    
    "infrastructure": "基建",
    "realestate": "房地产",
    
    "gold": "黄金",
    "nasdaq": "纳斯达克",
}

SECTOR_META = {
    
    "semiconductor": {
        "sector_type": "industry",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "上游（芯片设计/制造/封测/设备/材料）",
        "csrc_category": "电子-半导体",
        "related_concepts": ["ai_computing", "cpo", "ai_application", "deepseek"],
    },
    "electronics": {
        "sector_type": "industry",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "中上游（消费电子/PCB/被动元件/光学/面板/MLCC）",
        "csrc_category": "电子",
        "related_concepts": ["ai_computing", "cpo", "robot", "humanoid_robot", "consumer"],
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
        "chain_position": "跨行业概念（光模块/光芯片/CPO/光通信设备/玻璃基板）",
        "csrc_category": None,
        "spans_industries": ["电子", "通信"],
        "related_industries": ["electronics", "communication", "semiconductor"],
    },
    "ai_application": {
        "sector_type": "concept",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "跨行业概念（AI应用落地/办公AI/AI教育/AI医疗/AI营销/AI编程）- 同花顺2026.1.12新增",
        "csrc_category": None,
        "spans_industries": ["计算机", "传媒", "教育", "医药"],
        "related_industries": ["computer", "media", "ai_agent", "deepseek"],
    },
    "deepseek": {
        "sector_type": "concept",
        "tier": "T1",
        "tier_name": "AI算力硬科技",
        "chain_position": "跨行业概念（DeepSeek大模型/国产AI/开源大模型/R1推理模型）- 同花顺2025.2.4新增",
        "csrc_category": None,
        "spans_industries": ["计算机", "电子", "通信"],
        "related_industries": ["computer", "ai_computing", "ai_application", "ai_agent"],
    },

    
    "computer": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中游（软件/信创/云计算/网络安全/AI应用）",
        "csrc_category": "计算机",
        "related_concepts": ["ai_computing", "robot", "ai_agent", "deepseek", "ai_application"],
    },
    "communication": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中上游（运营商/通信设备/光纤光缆/卫星通信/卫星互联网）",
        "csrc_category": "通信",
        "related_concepts": ["cpo", "ai_computing", "satellite_internet"],
    },
    "military": {
        "sector_type": "industry",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "中下游（航空航天/军工电子/舰船/兵器/军工材料/商业航天）",
        "csrc_category": "国防军工",
        "related_concepts": ["satellite_internet", "low_altitude"],
    },
    "robot": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（工业机器人/服务机器人/减速器/伺服电机/传感器）",
        "csrc_category": None,
        "spans_industries": ["机械", "电子", "计算机", "汽车"],
        "related_industries": ["electronics", "computer", "military", "humanoid_robot"],
    },
    "humanoid_robot": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（人形机器人/具身智能/机器人关节/丝杠/执行器/特斯拉Optimus）- 同花顺2026年主线",
        "csrc_category": None,
        "spans_industries": ["机械", "电子", "计算机", "汽车"],
        "related_industries": ["robot", "electronics", "computer", "ai_agent"],
    },
    "ai_agent": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（AI智能体/Agent/自主智能体/MCP/AI助手/智能工作流）- 同花顺2025.1.24新增",
        "csrc_category": None,
        "spans_industries": ["计算机", "传媒", "电子"],
        "related_industries": ["computer", "ai_application", "deepseek", "media"],
    },
    "low_altitude": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（低空经济/eVTOL/飞行汽车/无人机/通航/低空基建）- 2026新质生产力重点",
        "csrc_category": None,
        "spans_industries": ["国防军工", "计算机", "电子", "交通运输"],
        "related_industries": ["military", "communication", "electronics"],
    },
    "satellite_internet": {
        "sector_type": "concept",
        "tier": "T2",
        "tier_name": "高端制造/智能科技",
        "chain_position": "跨行业概念（卫星互联网/星链/商业航天/低轨卫星/卫星通信/SpaceX概念）",
        "csrc_category": None,
        "spans_industries": ["国防军工", "通信", "电子"],
        "related_industries": ["military", "communication", "electronics"],
    },

    
    "newenergy": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "中下游（光伏/风电/新能源车/氢能/储能系统）",
        "csrc_category": "电力设备-新能源",
        "related_concepts": ["solid_battery"],
    },
    "battery": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "中上游（锂电池/动力电池/储能电池/正负极/电解液/隔膜）",
        "csrc_category": "电力设备-电池",
        "related_concepts": ["newenergy", "solid_battery"],
    },
    "power_grid": {
        "sector_type": "industry",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "上游（特高压/智能电网/输变电/配网/电力信息化）",
        "csrc_category": "电力设备-电网",
        "related_concepts": ["nuclear_fusion"],
    },
    "solid_battery": {
        "sector_type": "concept",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "跨行业概念（固态电池/全固态电池/半固态电池/固态电解质）- 下一代电池技术",
        "csrc_category": None,
        "spans_industries": ["电力设备", "有色金属", "化工"],
        "related_industries": ["battery", "newenergy", "nonferrous", "chemical"],
    },
    "nuclear_fusion": {
        "sector_type": "concept",
        "tier": "T3",
        "tier_name": "新能源/电力设备",
        "chain_position": "跨行业概念（可控核聚变/人造太阳/聚变装置/紧凑型聚变）- 同花顺2026.1.23新增",
        "csrc_category": None,
        "spans_industries": ["电力设备", "建筑装饰", "有色金属", "核工业"],
        "related_industries": ["power_grid", "infrastructure", "nonferrous"],
    },

    
    "medicine": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "全链条（化药/中药/医疗器械/医疗服务/医药流通）",
        "csrc_category": "医药生物",
        "related_concepts": ["biotech", "ai_application"],
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
        "chain_position": "中游（调味品/乳制品/休闲食品/啤酒/饮料/MLCC食品级应用）",
        "csrc_category": "食品饮料-食品",
        "related_concepts": ["consumer"],
    },
    "appliance": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（白色家电/小家电/厨电/智能家居/机器人家电）",
        "csrc_category": "家用电器",
        "related_concepts": ["consumer", "humanoid_robot"],
    },
    "tourism": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（旅游/酒店/免税/景区/餐饮/航空/社会服务）",
        "csrc_category": "社会服务",
        "related_concepts": ["consumer", "low_altitude"],
    },
    "media": {
        "sector_type": "industry",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "下游（游戏/影视/广告/出版/直播/AI应用/AI智能体）",
        "csrc_category": "传媒",
        "related_concepts": ["ai_application", "ai_agent"],
    },
    "biotech": {
        "sector_type": "concept",
        "tier": "T4",
        "tier_name": "消费医疗/文化传媒",
        "chain_position": "跨行业概念（创新药研发/CXO/生物医药/基因治疗/GLP-1/ADC）",
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
        "chain_position": "上游（铜/铝/锌/锂/稀土/黄金-工业金属/小金属）",
        "csrc_category": "有色金属",
        "related_concepts": ["solid_battery"],
    },
    "chemical": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "中游（基础化工/新材料/煤化工/化纤/农化/玻璃基板材料）",
        "csrc_category": "基础化工",
        "related_concepts": ["cpo", "solid_battery"],
    },
    "steel": {
        "sector_type": "industry",
        "tier": "V2",
        "tier_name": "周期资源（价值防御）",
        "chain_position": "中游（普钢/特钢/铁矿石/钢材加工）",
        "csrc_category": "钢铁",
        "related_concepts": [],
    },

    
    "infrastructure": {
        "sector_type": "industry",
        "tier": "V3",
        "tier_name": "基建地产（价值防御）",
        "chain_position": "中上游（建筑/建材/工程机械/铁路/港口/雅下水电）",
        "csrc_category": "建筑装饰/建筑材料",
        "related_concepts": ["nuclear_fusion", "low_altitude"],
    },
    "realestate": {
        "sector_type": "industry",
        "tier": "V3",
        "tier_name": "基建地产（价值防御）",
        "chain_position": "下游（房地产开发/物业/家居/中介）",
        "csrc_category": "房地产",
        "related_concepts": [],
    },

    
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
        "chain_position": "海外市场（纳斯达克100/美股科技巨头/AI美股）",
        "csrc_category": None,
        "spans_industries": ["海外市场"],
        "related_industries": [],
    },
}

SECTOR_CATEGORIES = [
    {
        "code": "T1",
        "name": "第一梯队·AI算力硬科技",
        "description": "AI全产业链：半导体/电子为硬件基础，AI算力/CPO/光通信为基建层，AI应用/DeepSeek为软件落地层，市场最强弹性",
        "children": ["semiconductor", "electronics", "ai_computing", "cpo", "ai_application", "deepseek"],
    },
    {
        "code": "T2",
        "name": "第二梯队·高端制造/智能科技",
        "description": "新质生产力方向：计算机/通信/军工为标准行业，人形机器人/AI智能体/低空经济/卫星互联网为2026核心赛道",
        "children": ["computer", "communication", "military", "robot", "humanoid_robot", "ai_agent", "low_altitude", "satellite_internet"],
    },
    {
        "code": "T3",
        "name": "第三梯队·新能源/电力设备",
        "description": "清洁能源+未来能源：光伏/风电/锂电/电网为基本盘，固态电池/可控核聚变为下一代技术方向",
        "children": ["newenergy", "battery", "power_grid", "solid_battery", "nuclear_fusion"],
    },
    {
        "code": "T4",
        "name": "第四梯队·消费医疗/文化传媒",
        "description": "稳健成长板块：医药/消费/家电/文旅/传媒为标准行业，创新药/大消费为跨行业概念，AI赋能消费升级",
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
        "description": "上游周期品：煤炭/石油/有色/化工/钢铁，通胀受益+高股息，受益新能源材料需求",
        "children": ["coal", "crude_oil", "nonferrous", "chemical", "steel"],
    },
    {
        "code": "V3",
        "name": "价值防御·基建地产",
        "description": "稳增长板块：基建/建材/工程机械/房地产，政策驱动型，受益核聚变/低空经济基建",
        "children": ["infrastructure", "realestate"],
    },
    {
        "code": "DEF",
        "name": "防御资产/海外",
        "description": "避险与海外配置：黄金为避险概念，纳斯达克为海外科技指数",
        "children": ["gold", "nasdaq"],
    },
]

INDUSTRY_SECTORS = [code for code, meta in SECTOR_META.items() if meta["sector_type"] == "industry"]
CONCEPT_SECTORS = [code for code, meta in SECTOR_META.items() if meta["sector_type"] == "concept"]

TIER_COLORS = {
    "T1": "#ef4444",
    "T2": "#f97316",
    "T3": "#22c55e",
    "T4": "#3b82f6",
    "V1": "#64748b",
    "V2": "#78716c",
    "V3": "#a16207",
    "DEF": "#eab308",
}

VERSION = "3.0.0"
LAST_UPDATED = "2026-08-05"
UPDATE_NOTES = [
    "对齐同花顺2026年最新板块分类标准",
    "新增AI应用板块（同花顺2026.1.12新增概念）",
    "新增DeepSeek概念板块（同花顺2025.2.4新增）",
    "新增AI智能体板块（同花顺2025.1.24新增）",
    "新增人形机器人板块（2026年市场主线，独立于工业机器人）",
    "新增可控核聚变板块（同花顺2026.1.23新增）",
    "新增低空经济板块（2026新质生产力重点方向）",
    "新增卫星互联网板块（商业航天核心赛道）",
    "新增固态电池板块（下一代电池技术）",
    "更新电子板块描述，纳入MLCC等热门细分",
    "更新化工板块描述，纳入玻璃基板材料方向",
    "板块总数从31个增加到39个",
]


def get_sector_type(code: str) -> str:
    return SECTOR_META.get(code, {}).get("sector_type", "industry")


def get_sector_tier(code: str) -> str:
    return SECTOR_META.get(code, {}).get("tier", "T4")


def get_related_sectors(code: str) -> List[str]:
    meta = SECTOR_META.get(code, {})
    if meta.get("sector_type") == "concept":
        return meta.get("related_industries", [])
    else:
        return meta.get("related_concepts", [])


def get_version_info() -> Dict:
    return {
        "version": VERSION,
        "last_updated": LAST_UPDATED,
        "total_sectors": len(SECTOR_NAMES),
        "industry_count": len(INDUSTRY_SECTORS),
        "concept_count": len(CONCEPT_SECTORS),
        "update_notes": UPDATE_NOTES,
    }


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
            
            
            empty_data = _empty_sector_data()
            for record in deduped:
                sectors = record.get("sectors", {})
                for sector_code in SECTOR_NAMES:
                    if sector_code not in sectors:
                        sectors[sector_code] = dict(empty_data)
                record["sectors"] = sectors
            
            if changed:
                data["records"] = deduped
        return data
    return {"records": []}


def save_history(history: Dict):
    history_file = os.path.join(DATA_DIR, "history.json")
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp_file = history_file + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, history_file)


def add_record(sector_indices: Dict[str, Dict], analysis_results: Dict):
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
        "version_info": get_version_info(),
    }
