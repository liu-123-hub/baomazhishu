import request from './request'

export const SECTOR_CATEGORIES = [
  {
    code: 'finance',
    name: '大金融',
    children: ['bank', 'securities', 'insurance']
  },
  {
    code: 'consumption',
    name: '大消费',
    children: ['baijiu', 'food', 'medicine', 'appliance', 'tourism', 'biotech', 'consumer']
  },
  {
    code: 'technology',
    name: '大科技',
    children: ['electronics', 'computer', 'communication', 'media', 'cpo', 'semiconductor']
  },
  {
    code: 'cyclical',
    name: '大周期',
    children: ['nonferrous', 'coal', 'chemical', 'steel', 'realestate', 'infrastructure', 'newenergy']
  },
  {
    code: 'others',
    name: '其他',
    children: ['nasdaq', 'gold']
  }
]

export const SECTOR_NAMES = {
  bank: '银行',
  securities: '券商',
  insurance: '保险',
  baijiu: '白酒',
  food: '食品',
  medicine: '医药',
  appliance: '家电',
  tourism: '文旅',
  biotech: '创新药',
  consumer: '消费',
  electronics: '电子',
  computer: '计算机',
  communication: '通信',
  media: '传媒',
  cpo: 'CPO通信',
  semiconductor: '半导体',
  nonferrous: '有色',
  coal: '煤炭',
  chemical: '化工',
  steel: '钢铁',
  realestate: '地产',
  infrastructure: '基建',
  newenergy: '新能源',
  nasdaq: '纳斯达克',
  gold: '黄金'
}

export const SECTOR_COLORS = {
  bank: '#4ecdc4',
  securities: '#0ea5e9',
  insurance: '#06b6d4',
  baijiu: '#ef4444',
  food: '#f59e0b',
  medicine: '#f472b6',
  appliance: '#a78bfa',
  tourism: '#fb923c',
  biotech: '#ec4899',
  consumer: '#fbbf24',
  electronics: '#22c55e',
  computer: '#10b981',
  communication: '#00ff88',
  media: '#34d399',
  cpo: '#60a5fa',
  semiconductor: '#ff6b6b',
  nonferrous: '#a855f7',
  coal: '#78716c',
  chemical: '#84cc16',
  steel: '#64748b',
  realestate: '#b45309',
  infrastructure: '#0d9488',
  newenergy: '#f43f5e',
  nasdaq: '#00d4ff',
  gold: '#ffd700'
}

export const CATEGORY_COLORS = {
  finance: '#0ea5e9',
  consumption: '#f59e0b',
  technology: '#22c55e',
  cyclical: '#a855f7',
  others: '#94a3b8'
}

export function getDashboardOverview() {
  return request.get('/dashboard/overview')
}

export function getLineChartData(sectors, days = 7) {
  const params = {}
  if (sectors) params.sectors = sectors
  if (days) params.days = days
  return request.get('/dashboard/line-chart', { params })
}

export function getSectorDetail(code) {
  return request.get('/dashboard/sector-detail', { params: { code } })
}

export function getHistoryTrend(code, days = 7) {
  const params = {}
  if (code) params.code = code
  if (days) params.days = days
  return request.get('/dashboard/history', { params })
}

export function getMarketData(sector) {
  const params = {}
  if (sector) params.sector = sector
  return request.get('/dashboard/market-data', { params })
}

export function getEtfCorrelation(sector, days = 30) {
  return request.get('/dashboard/etf-correlation', { params: { sector, days } })
}

export function getCapitalFlowSummary() {
  return request.get('/dashboard/capital-flow')
}

export function getCapitalFlowDetail(dataType, tradeDate) {
  const params = { type: dataType }
  if (tradeDate) params.date = tradeDate
  return request.get('/dashboard/capital-flow/detail', { params })
}

export function getSystemHealth() {
  return request.get('/system/health')
}

export function getSystemStatus() {
  return request.get('/system/status')
}

export function clearSystemCache() {
  return request.post('/system/cache/clear')
}

export function getCollectionStatus() {
  return request.get('/system/collection-status')
}

export function getSourceHealth() {
  return request.get('/system/source-health')
}

export const dashboardApi = {
  getOverview: getDashboardOverview,
  getLineChart: getLineChartData,
  getSectorDetail,
  getHistory: getHistoryTrend,
  getMarketData,
  getEtfCorrelation,
  getCapitalFlowSummary,
  getCapitalFlowDetail
}

export const systemApi = {
  health: getSystemHealth,
  status: getSystemStatus,
  clearCache: clearSystemCache,
  collectionStatus: getCollectionStatus,
  sourceHealth: getSourceHealth
}

export default {
  dashboard: dashboardApi,
  system: systemApi,
  SECTOR_NAMES,
  SECTOR_COLORS
}
