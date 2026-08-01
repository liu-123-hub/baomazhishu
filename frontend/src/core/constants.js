/**
 * 板块分类体系 v2.0（2026-07-30 重构）
 *
 * 两大维度：
 * - 投资风格维度：4大梯队成长赛道(T1~T4) + 价值防御(V1~V3) + 防御资产(DEF)
 * - 板块属性维度：标准行业板块(industry) vs 跨行业概念赛道(concept)
 *
 * 注意：SECTOR_NAMES 为唯一真值来源，需与 analyzer/index_calculator.py 保持一致
 */

export const PLATFORM = {
  WEB: 'web',
  MOBILE: 'mobile'
}

// ──── 板块代码 → 中文名称（与后端 index_calculator.py SECTOR_NAMES 完全一致）────
export const SECTOR_NAMES = {
  // T1 第一梯队：AI算力硬科技
  semiconductor: '半导体',
  electronics: '电子',
  ai_computing: 'AI算力',
  cpo: 'CPO光通信',
  // T2 第二梯队：高端制造/智能科技
  computer: '计算机',
  communication: '通信',
  military: '军工',
  robot: '机器人',
  // T3 第三梯队：新能源/电力设备
  newenergy: '新能源',
  battery: '电池',
  power_grid: '电力设备',
  // T4 第四梯队：消费医疗/文化传媒
  medicine: '医药',
  baijiu: '白酒',
  food: '食品饮料',
  appliance: '家电',
  tourism: '文旅',
  media: '传媒',
  biotech: '创新药',
  consumer: '大消费',
  // V1 价值防御：大金融
  bank: '银行',
  securities: '券商',
  insurance: '保险',
  // V2 价值防御：周期资源
  coal: '煤炭',
  crude_oil: '石油石化',
  nonferrous: '有色金属',
  chemical: '化工',
  steel: '钢铁',
  // V3 价值防御：基建地产
  infrastructure: '基建',
  realestate: '房地产',
  // DEF 防御资产/海外
  gold: '黄金',
  nasdaq: '纳斯达克'
}

// ──── 板块元数据：属性类型 + 梯队 + 产业链位置 ────
export const SECTOR_META = {
  // T1
  semiconductor: { type: 'industry', tier: 'T1', tierName: 'AI算力硬科技', chain: '上游(芯片设计/制造/封测/设备/材料)', csrc: '电子-半导体' },
  electronics: { type: 'industry', tier: 'T1', tierName: 'AI算力硬科技', chain: '中上游(消费电子/PCB/元件/光学)', csrc: '电子' },
  ai_computing: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(GPU/服务器/IDC/液冷/HBM)', csrc: null, spans: ['电子','计算机','通信'] },
  cpo: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(光模块/光芯片/CPO/光通信)', csrc: null, spans: ['电子','通信'] },
  // T2
  computer: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中游(软件/信创/云计算/AI应用)', csrc: '计算机' },
  communication: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中上游(运营商/通信设备/光纤)', csrc: '通信' },
  military: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中下游(航空航天/军工电子/舰船)', csrc: '国防军工' },
  robot: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(人形机器人/减速器/伺服/传感器)', csrc: null, spans: ['机械','电子','计算机','汽车'] },
  // T3
  newenergy: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '中下游(光伏/风电/新能源车/储能)', csrc: '电力设备-新能源' },
  battery: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '中上游(锂电/动力电池/正负极/电解液)', csrc: '电力设备-电池' },
  power_grid: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '上游(特高压/智能电网/输变电)', csrc: '电力设备-电网' },
  // T4
  medicine: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '全链条(化药/中药/器械/医疗服务)', csrc: '医药生物' },
  baijiu: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '中上游(高端/次高端/区域白酒)', csrc: '食品饮料-白酒' },
  food: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '中游(调味品/乳制品/休闲食品/啤酒)', csrc: '食品饮料-食品' },
  appliance: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(白电/小家电/厨电/智能家居)', csrc: '家用电器' },
  tourism: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(旅游/酒店/免税/景区/航空)', csrc: '社会服务' },
  media: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(游戏/影视/广告/出版/AI应用)', csrc: '传媒' },
  biotech: { type: 'concept', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '跨行业(创新药/CXO/生物医药/基因治疗)', csrc: null, spans: ['医药生物'] },
  consumer: { type: 'concept', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '跨行业(必选+可选消费，跨白酒/食品/家电/文旅)', csrc: null, spans: ['食品饮料','家电','社服','零售'] },
  // V1
  bank: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(国有大行/股份行/城商行)', csrc: '银行' },
  securities: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(券商/投行/资管/经纪)', csrc: '非银金融-证券' },
  insurance: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(寿险/财险/保险经纪)', csrc: '非银金融-保险' },
  // V2
  coal: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上游(动力煤/焦煤/开采/煤化工)', csrc: '煤炭' },
  crude_oil: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上中游(开采/油气服务/炼化/销售)', csrc: '石油石化' },
  nonferrous: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上游(铜/铝/锌/锂/稀土)', csrc: '有色金属' },
  chemical: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '中游(基础化工/新材料/煤化工)', csrc: '基础化工' },
  steel: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '中游(普钢/特钢/铁矿石)', csrc: '钢铁' },
  // V3
  infrastructure: { type: 'industry', tier: 'V3', tierName: '基建地产（价值防御）', chain: '中上游(建筑/建材/工程机械/铁路)', csrc: '建筑/建材' },
  realestate: { type: 'industry', tier: 'V3', tierName: '基建地产（价值防御）', chain: '下游(开发/物业/家居/中介)', csrc: '房地产' },
  // DEF
  gold: { type: 'concept', tier: 'DEF', tierName: '防御资产', chain: '避险资产(黄金现货/黄金股/ETF)', csrc: null, spans: ['有色金属','贵金属'] },
  nasdaq: { type: 'concept', tier: 'DEF', tierName: '海外资产', chain: '海外(纳斯达克100/美股科技)', csrc: null, spans: ['海外市场'] }
}

// ──── 一级分类（梯队体系）────
export const SECTOR_CATEGORIES = [
  { code: 'T1', name: '第一梯队·AI算力硬科技', description: 'AI算力产业链：半导体/电子为核心，CPO/AI算力为跨行业概念主线，市场最强弹性', children: ['semiconductor', 'electronics', 'ai_computing', 'cpo'] },
  { code: 'T2', name: '第二梯队·高端制造/智能科技', description: '产业升级方向：计算机/通信/军工为标准行业，机器人为跨行业概念赛道', children: ['computer', 'communication', 'military', 'robot'] },
  { code: 'T3', name: '第三梯队·新能源/电力设备', description: '清洁能源产业链：新能源/电池/电力设备上中下游全覆盖', children: ['newenergy', 'battery', 'power_grid'] },
  { code: 'T4', name: '第四梯队·消费医疗/文化传媒', description: '稳健成长板块：医药/消费/家电/文旅/传媒为标准行业，创新药/大消费为跨行业概念', children: ['medicine', 'baijiu', 'food', 'appliance', 'tourism', 'media', 'biotech', 'consumer'] },
  { code: 'V1', name: '价值防御·大金融', description: '金融三剑客：银行/券商/保险，低估值高股息防御板块', children: ['bank', 'securities', 'insurance'] },
  { code: 'V2', name: '价值防御·周期资源', description: '上游周期品：煤炭/石油/有色/化工/钢铁，通胀受益+高股息', children: ['coal', 'crude_oil', 'nonferrous', 'chemical', 'steel'] },
  { code: 'V3', name: '价值防御·基建地产', description: '稳增长板块：基建/建材/工程机械/房地产，政策驱动型', children: ['infrastructure', 'realestate'] },
  { code: 'DEF', name: '防御资产/海外', description: '避险与海外配置：黄金为避险概念，纳斯达克为海外科技指数', children: ['gold', 'nasdaq'] }
]

// ──── 板块颜色（按梯队色系，同一梯队使用同色系渐变）────
export const SECTOR_COLORS = {
  // T1 红色系（最热）
  semiconductor: '#dc2626', electronics: '#ef4444', ai_computing: '#f87171', cpo: '#fca5a5',
  // T2 橙色系（高景气）
  computer: '#ea580c', communication: '#f97316', military: '#fb923c', robot: '#fdba74',
  // T3 绿色系（成长）
  newenergy: '#15803d', battery: '#22c55e', power_grid: '#4ade80',
  // T4 蓝色系（稳健）
  medicine: '#1d4ed8', baijiu: '#3b82f6', food: '#60a5fa', appliance: '#93c5fd',
  tourism: '#2563eb', media: '#7c3aed', biotech: '#ec4899', consumer: '#fbbf24',
  // V1 灰色系（防御）
  bank: '#475569', securities: '#64748b', insurance: '#94a3b8',
  // V2 暖灰/棕色系（周期）
  coal: '#57534e', crude_oil: '#78716c', nonferrous: '#a8a29e', chemical: '#d6d3d1', steel: '#78716c',
  // V3 褐色系（稳增长）
  infrastructure: '#92400e', realestate: '#b45309',
  // DEF 金色系
  gold: '#fbbf24', nasdaq: '#06b6d4'
}

// ──── 梯队分类颜色 ────
export const CATEGORY_COLORS = {
  T1: '#ef4444', T2: '#f97316', T3: '#22c55e', T4: '#3b82f6',
  V1: '#64748b', V2: '#78716c', V3: '#a16207', DEF: '#eab308'
}

// 梯队中文名称映射
export const TIER_NAMES = {
  T1: '第一梯队·AI算力硬科技',
  T2: '第二梯队·高端制造/智能科技',
  T3: '第三梯队·新能源/电力设备',
  T4: '第四梯队·消费医疗/文化传媒',
  V1: '价值防御·大金融',
  V2: '价值防御·周期资源',
  V3: '价值防御·基建地产',
  DEF: '防御资产/海外'
}

// 板块属性类型标签
export const SECTOR_TYPE_LABELS = {
  industry: '标准行业',
  concept: '概念赛道'
}

// 指数分级
export const INDEX_LEVELS = {
  EXTREME_FEAR: { max: 20, label: '极度恐慌', color: '#dc2626', bg: '#fef2f2' },
  FEAR: { max: 40, label: '恐慌', color: '#ea580c', bg: '#fff7ed' },
  NEUTRAL: { max: 60, label: '中性', color: '#ca8a04', bg: '#fefce8' },
  GREED: { max: 80, label: '贪婪', color: '#16a34a', bg: '#f0fdf4' },
  EXTREME_GREED: { max: 100, label: '极度贪婪', color: '#059669', bg: '#ecfdf5' }
}

export const REFRESH_INTERVAL = 30 * 1000

export const APP_CONFIG = {
  name: '宝妈指数',
  version: '2.1.0',
  description: '跨平台金融市场情绪分析系统',
  apiBaseUrl: '/api',
  defaultDays: 7,
  maxDays: 365
}

// 工具函数
export function getSectorType(code) {
  return SECTOR_META[code]?.type || 'industry'
}

export function getSectorTier(code) {
  return SECTOR_META[code]?.tier || 'T4'
}

export function isConceptSector(code) {
  return SECTOR_META[code]?.type === 'concept'
}

export function isGrowthSector(code) {
  const tier = getSectorTier(code)
  return tier.startsWith('T')
}
