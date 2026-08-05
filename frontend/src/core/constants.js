export const PLATFORM = {
  WEB: 'web',
  MOBILE: 'mobile'
}

export const SECTOR_NAMES = {
  // T1：AI算力硬科技
  semiconductor: '半导体',
  electronics: '电子',
  ai_computing: 'AI算力',
  cpo: 'CPO光通信',
  ai_application: 'AI应用',
  deepseek: 'DeepSeek概念',
  // T2：高端制造/智能科技
  computer: '计算机',
  communication: '通信',
  military: '军工',
  robot: '机器人',
  humanoid_robot: '人形机器人',
  ai_agent: 'AI智能体',
  low_altitude: '低空经济',
  satellite_internet: '卫星互联网',
  // T3：新能源/电力设备
  newenergy: '新能源',
  battery: '电池',
  power_grid: '电力设备',
  solid_battery: '固态电池',
  nuclear_fusion: '可控核聚变',
  // T4：消费医疗/文化传媒
  medicine: '医药',
  baijiu: '白酒',
  food: '食品饮料',
  appliance: '家电',
  tourism: '文旅',
  media: '传媒',
  biotech: '创新药',
  consumer: '大消费',
  // V1：大金融
  bank: '银行',
  securities: '券商',
  insurance: '保险',
  // V2：周期资源
  coal: '煤炭',
  crude_oil: '石油石化',
  nonferrous: '有色金属',
  chemical: '化工',
  steel: '钢铁',
  // V3：基建地产
  infrastructure: '基建',
  realestate: '房地产',
  // DEF：防御资产/海外
  gold: '黄金',
  nasdaq: '纳斯达克'
}

export const SECTOR_META = {
  // T1
  semiconductor: { type: 'industry', tier: 'T1', tierName: 'AI算力硬科技', chain: '上游(芯片设计/制造/封测/设备/材料)', csrc: '电子-半导体' },
  electronics: { type: 'industry', tier: 'T1', tierName: 'AI算力硬科技', chain: '中上游(消费电子/PCB/元件/光学/MLCC)', csrc: '电子' },
  ai_computing: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(GPU/服务器/IDC/液冷/HBM)', csrc: null, spans: ['电子','计算机','通信'] },
  cpo: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(光模块/光芯片/CPO/玻璃基板)', csrc: null, spans: ['电子','通信'] },
  ai_application: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(AI应用落地/办公AI/AI教育/AI医疗)', csrc: null, spans: ['计算机','传媒','教育','医药'], isNew: true },
  deepseek: { type: 'concept', tier: 'T1', tierName: 'AI算力硬科技', chain: '跨行业(DeepSeek/国产大模型/R1推理/开源AI)', csrc: null, spans: ['计算机','电子','通信'], isNew: true },
  // T2
  computer: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中游(软件/信创/云计算/AI应用)', csrc: '计算机' },
  communication: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中上游(运营商/通信设备/卫星互联网)', csrc: '通信' },
  military: { type: 'industry', tier: 'T2', tierName: '高端制造/智能科技', chain: '中下游(航空航天/军工电子/商业航天)', csrc: '国防军工' },
  robot: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(工业机器人/服务机器人/减速器)', csrc: null, spans: ['机械','电子','计算机','汽车'] },
  humanoid_robot: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(人形机器人/具身智能/Optimus/丝杠)', csrc: null, spans: ['机械','电子','计算机','汽车'], isNew: true },
  ai_agent: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(AI智能体/Agent/MCP/智能工作流)', csrc: null, spans: ['计算机','传媒','电子'], isNew: true },
  low_altitude: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(低空经济/eVTOL/飞行汽车/无人机)', csrc: null, spans: ['军工','计算机','电子','交运'], isNew: true },
  satellite_internet: { type: 'concept', tier: 'T2', tierName: '高端制造/智能科技', chain: '跨行业(卫星互联网/星链/商业航天/低轨卫星)', csrc: null, spans: ['军工','通信','电子'], isNew: true },
  // T3
  newenergy: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '中下游(光伏/风电/新能源车/储能)', csrc: '电力设备-新能源' },
  battery: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '中上游(锂电/动力电池/正负极/电解液)', csrc: '电力设备-电池' },
  power_grid: { type: 'industry', tier: 'T3', tierName: '新能源/电力设备', chain: '上游(特高压/智能电网/输变电/核聚变)', csrc: '电力设备-电网' },
  solid_battery: { type: 'concept', tier: 'T3', tierName: '新能源/电力设备', chain: '跨行业(固态电池/全固态/半固态/固态电解质)', csrc: null, spans: ['电力设备','有色','化工'], isNew: true },
  nuclear_fusion: { type: 'concept', tier: 'T3', tierName: '新能源/电力设备', chain: '跨行业(可控核聚变/人造太阳/聚变装置)', csrc: null, spans: ['电力设备','建筑','有色','核工业'], isNew: true },
  // T4
  medicine: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '全链条(化药/中药/器械/医疗服务)', csrc: '医药生物' },
  baijiu: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '中上游(高端/次高端/区域白酒)', csrc: '食品饮料-白酒' },
  food: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '中游(调味品/乳制品/休闲食品/啤酒)', csrc: '食品饮料-食品' },
  appliance: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(白电/小家电/厨电/智能家居)', csrc: '家用电器' },
  tourism: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(旅游/酒店/免税/景区/航空/社会服务)', csrc: '社会服务' },
  media: { type: 'industry', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '下游(游戏/影视/广告/AI应用/AI智能体)', csrc: '传媒' },
  biotech: { type: 'concept', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '跨行业(创新药/CXO/生物医药/GLP-1)', csrc: null, spans: ['医药生物'] },
  consumer: { type: 'concept', tier: 'T4', tierName: '消费医疗/文化传媒', chain: '跨行业(必选+可选消费，跨白酒/食品/家电/文旅)', csrc: null, spans: ['食品饮料','家电','社服','零售'] },
  // V1
  bank: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(国有大行/股份行/城商行)', csrc: '银行' },
  securities: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(券商/投行/资管/经纪)', csrc: '非银金融-证券' },
  insurance: { type: 'industry', tier: 'V1', tierName: '大金融（价值防御）', chain: '全链条(寿险/财险/保险经纪)', csrc: '非银金融-保险' },
  // V2
  coal: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上游(动力煤/焦煤/开采/煤化工)', csrc: '煤炭' },
  crude_oil: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上中游(开采/油气服务/炼化/销售)', csrc: '石油石化' },
  nonferrous: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '上游(铜/铝/锌/锂/稀土/小金属)', csrc: '有色金属' },
  chemical: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '中游(基础化工/新材料/玻璃基板材料)', csrc: '基础化工' },
  steel: { type: 'industry', tier: 'V2', tierName: '周期资源（价值防御）', chain: '中游(普钢/特钢/铁矿石)', csrc: '钢铁' },
  // V3
  infrastructure: { type: 'industry', tier: 'V3', tierName: '基建地产（价值防御）', chain: '中上游(建筑/建材/工程机械/雅下水电)', csrc: '建筑/建材' },
  realestate: { type: 'industry', tier: 'V3', tierName: '基建地产（价值防御）', chain: '下游(开发/物业/家居/中介)', csrc: '房地产' },
  // DEF
  gold: { type: 'concept', tier: 'DEF', tierName: '防御资产', chain: '避险资产(黄金现货/黄金股/ETF)', csrc: null, spans: ['有色金属','贵金属'] },
  nasdaq: { type: 'concept', tier: 'DEF', tierName: '海外资产', chain: '海外(纳斯达克100/美股科技/AI美股)', csrc: null, spans: ['海外市场'] }
}

export const SECTOR_CATEGORIES = [
  { code: 'T1', name: '第一梯队·AI算力硬科技', description: 'AI全产业链：半导体/电子为硬件基础，AI算力/CPO为基建层，AI应用/DeepSeek为软件落地层', children: ['semiconductor', 'electronics', 'ai_computing', 'cpo', 'ai_application', 'deepseek'] },
  { code: 'T2', name: '第二梯队·高端制造/智能科技', description: '新质生产力：计算机/通信/军工为基础，人形机器人/AI智能体/低空经济/卫星互联网为2026核心赛道', children: ['computer', 'communication', 'military', 'robot', 'humanoid_robot', 'ai_agent', 'low_altitude', 'satellite_internet'] },
  { code: 'T3', name: '第三梯队·新能源/电力设备', description: '清洁能源+未来能源：光伏/风电/锂电/电网为基本盘，固态电池/可控核聚变为下一代技术', children: ['newenergy', 'battery', 'power_grid', 'solid_battery', 'nuclear_fusion'] },
  { code: 'T4', name: '第四梯队·消费医疗/文化传媒', description: '稳健成长：医药/消费/家电/文旅/传媒为标准行业，创新药/大消费为跨行业概念', children: ['medicine', 'baijiu', 'food', 'appliance', 'tourism', 'media', 'biotech', 'consumer'] },
  { code: 'V1', name: '价值防御·大金融', description: '金融三剑客：银行/券商/保险，低估值高股息防御板块', children: ['bank', 'securities', 'insurance'] },
  { code: 'V2', name: '价值防御·周期资源', description: '上游周期品：煤炭/石油/有色/化工/钢铁，通胀受益+高股息', children: ['coal', 'crude_oil', 'nonferrous', 'chemical', 'steel'] },
  { code: 'V3', name: '价值防御·基建地产', description: '稳增长板块：基建/建材/工程机械/房地产，政策驱动型', children: ['infrastructure', 'realestate'] },
  { code: 'DEF', name: '防御资产/海外', description: '避险与海外配置：黄金为避险概念，纳斯达克为海外科技指数', children: ['gold', 'nasdaq'] }
]

export const SECTOR_COLORS = {
  // T1 - 红色系
  semiconductor: '#dc2626', electronics: '#ef4444', ai_computing: '#f87171', cpo: '#fca5a5',
  ai_application: '#fecaca', deepseek: '#fee2e2',
  // T2 - 橙色系
  computer: '#c2410c', communication: '#ea580c', military: '#f97316', robot: '#fb923c',
  humanoid_robot: '#fdba74', ai_agent: '#fed7aa', low_altitude: '#ffedd5', satellite_internet: '#fff7ed',
  // T3 - 绿色系
  newenergy: '#15803d', battery: '#16a34a', power_grid: '#22c55e',
  solid_battery: '#4ade80', nuclear_fusion: '#86efac',
  // T4 - 蓝色系
  medicine: '#1d4ed8', baijiu: '#2563eb', food: '#3b82f6', appliance: '#60a5fa',
  tourism: '#2563eb', media: '#7c3aed', biotech: '#ec4899', consumer: '#fbbf24',
  // V1 - 灰色系
  bank: '#475569', securities: '#64748b', insurance: '#94a3b8',
  // V2 - 石灰色系
  coal: '#44403c', crude_oil: '#57534e', nonferrous: '#78716c', chemical: '#a8a29e', steel: '#d6d3d1',
  // V3 - 棕色系
  infrastructure: '#92400e', realestate: '#b45309',
  // DEF - 金色/青色
  gold: '#fbbf24', nasdaq: '#06b6d4'
}

export const CATEGORY_COLORS = {
  T1: '#ef4444', T2: '#f97316', T3: '#22c55e', T4: '#3b82f6',
  V1: '#64748b', V2: '#78716c', V3: '#a16207', DEF: '#eab308'
}

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

export const SECTOR_TYPE_LABELS = {
  industry: '标准行业',
  concept: '概念赛道'
}

export const NEW_SECTORS = ['ai_application', 'deepseek', 'humanoid_robot', 'ai_agent', 'low_altitude', 'satellite_internet', 'solid_battery', 'nuclear_fusion']

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
  version: '3.0.0',
  description: '跨平台金融市场情绪分析系统',
  apiBaseUrl: '/api',
  defaultDays: 7,
  maxDays: 365,
  lastUpdated: '2026-08-05',
  updateNotes: [
    '对齐同花顺2026年最新板块分类标准',
    '新增AI应用、DeepSeek概念、AI智能体、人形机器人',
    '新增可控核聚变、低空经济、卫星互联网、固态电池',
    '板块总数从31个增加到39个'
  ]
}

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

export function isNewSector(code) {
  return NEW_SECTORS.includes(code)
}
