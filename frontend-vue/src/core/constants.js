export const PLATFORM = {
  WEB: 'web',
  TAURI: 'tauri',
  ELECTRON: 'electron',
  MOBILE: 'mobile',
  CAPACITOR: 'capacitor'
}

export const SECTOR_CATEGORIES = [
  { code: 'finance', name: '大金融', children: ['bank', 'securities', 'insurance'] },
  { code: 'consumption', name: '大消费', children: ['baijiu', 'food', 'medicine', 'appliance', 'tourism', 'biotech', 'consumer'] },
  { code: 'technology', name: '大科技', children: ['electronics', 'computer', 'communication', 'media', 'cpo', 'semiconductor'] },
  { code: 'cyclical', name: '大周期', children: ['nonferrous', 'coal', 'chemical', 'steel', 'realestate', 'infrastructure', 'newenergy'] },
  { code: 'others', name: '其他', children: ['nasdaq', 'gold'] }
]

export const SECTOR_NAMES = {
  bank: '银行', securities: '券商', insurance: '保险',
  baijiu: '白酒', food: '食品', medicine: '医药', appliance: '家电',
  tourism: '文旅', biotech: '创新药', consumer: '消费',
  electronics: '电子', computer: '计算机', communication: '通信', media: '传媒',
  cpo: 'CPO通信', semiconductor: '半导体',
  nonferrous: '有色', coal: '煤炭', chemical: '化工', steel: '钢铁',
  realestate: '地产', infrastructure: '基建', newenergy: '新能源',
  nasdaq: '纳斯达克', gold: '黄金'
}

export const SECTOR_COLORS = {
  bank: '#4ecdc4', securities: '#0ea5e9', insurance: '#06b6d4',
  baijiu: '#ef4444', food: '#f59e0b', medicine: '#f472b6', appliance: '#a78bfa',
  tourism: '#fb923c', biotech: '#ec4899', consumer: '#fbbf24',
  electronics: '#22c55e', computer: '#10b981', communication: '#00ff88', media: '#34d399',
  cpo: '#60a5fa', semiconductor: '#ff6b6b',
  nonferrous: '#a855f7', coal: '#78716c', chemical: '#84cc16', steel: '#64748b',
  realestate: '#b45309', infrastructure: '#0d9488', newenergy: '#f43f5e',
  nasdaq: '#00d4ff', gold: '#ffd700'
}

export const CATEGORY_COLORS = {
  finance: '#0ea5e9', consumption: '#f59e0b',
  technology: '#22c55e', cyclical: '#a855f7', others: '#94a3b8'
}

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
  version: '2.0.0',
  description: '跨平台金融市场情绪分析系统',
  apiBaseUrl: '/api',
  defaultDays: 7,
  maxDays: 365
}
