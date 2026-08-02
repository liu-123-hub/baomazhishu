import axios from 'axios'
import { APP_CONFIG } from './constants.js'

let apiClient = null

const requestCache = new Map()
const CACHE_TTL = 5000

function getCacheKey(config) {
  return `${config.method || 'GET'}:${config.url}:${JSON.stringify(config.params || {})}`
}

function getCachedResponse(key) {
  const cached = requestCache.get(key)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data
  }
  requestCache.delete(key)
  return null
}

function setCachedResponse(key, data) {
  requestCache.set(key, { data, timestamp: Date.now() })
}

function getApiBaseUrl() {
  return APP_CONFIG.apiBaseUrl
}

export async function initApi() {
  updateApiClient()
  return apiClient
}

function updateApiClient() {
  const baseURL = getApiBaseUrl()
  apiClient = axios.create({
    baseURL,
    timeout: 15000,
    headers: { 'Content-Type': 'application/json' }
  })

  apiClient.interceptors.request.use(
    (config) => {
      config.metadata = { startTime: Date.now() }
      return config
    },
    (error) => Promise.reject(error)
  )

  apiClient.interceptors.response.use(
    (response) => {
      const data = response.data
      if (data && typeof data === 'object' && 'code' in data) {
        if (data.code === 200) {
          return data
        } else {
          const error = new Error(data.message || '请求失败')
          error.code = data.code
          error.data = data.data
          throw error
        }
      }
      return { code: 200, data, message: 'success' }
    },
    (error) => {
      if (error.code === 'ERR_NETWORK' || !error.response) {
        error.isNetworkError = true
        const isActuallyOnline = typeof navigator !== 'undefined' ? navigator.onLine : true
        if (isActuallyOnline) {
          error.errorType = 'backend_unreachable'
          error.userMessage = '后端服务未启动或不可达，请检查后端服务是否运行'
        } else {
          error.errorType = 'no_network'
          error.userMessage = '网络连接已断开，请检查网络连接'
        }
      } else if (error.response?.status === 404) {
        error.userMessage = '请求的资源不存在'
      } else if (error.response?.status === 500) {
        error.userMessage = '服务器内部错误'
      } else if (error.response?.status === 422) {
        error.userMessage = '请求参数错误'
      } else {
        error.userMessage = error.message || '请求失败'
      }
      return Promise.reject(error)
    }
  )
}

export function getApiClient() {
  if (!apiClient) {
    updateApiClient()
  }
  return apiClient
}

export async function request(config) {
  const method = (config.method || 'GET').toUpperCase()
  const useCache = method === 'GET' && !config.signal
  
  if (useCache) {
    const cacheKey = getCacheKey(config)
    const cached = getCachedResponse(cacheKey)
    if (cached) {
      return cached
    }
  }
  
  const response = await getApiClient()(config)
  
  if (useCache && response?.code === 200) {
    const cacheKey = getCacheKey(config)
    setCachedResponse(cacheKey, response)
  }
  
  return response
}

export const dashboardApi = {
  getOverview() {
    return request({ url: '/dashboard/overview', method: 'GET' })
  },
  getLineChart(sectors, days = 7, opts = {}) {
    const params = {}
    if (sectors) params.sectors = Array.isArray(sectors) ? sectors.join(',') : sectors
    if (days) params.days = days
    return request({ url: '/dashboard/line-chart', method: 'GET', params, signal: opts.signal })
  },
  getSectorDetail(code) {
    return request({ url: '/dashboard/sector-detail', method: 'GET', params: { code } })
  },
  getHistory(code, days = 7) {
    const params = {}
    if (code) params.code = code
    if (days) params.days = days
    return request({ url: '/dashboard/history', method: 'GET', params })
  },
  getMarketData(sector) {
    const params = {}
    if (sector) params.sector = sector
    return request({ url: '/dashboard/market-data', method: 'GET', params })
  },
  getEtfCorrelation(sector, days = 30) {
    return request({ url: '/dashboard/etf-correlation', method: 'GET', params: { sector, days } })
  },
  getCapitalFlowSummary() {
    return request({ url: '/dashboard/capital-flow', method: 'GET' })
  },
  getCapitalFlowDetail(type, date) {
    const params = { type }
    if (date) params.date = date
    return request({ url: '/dashboard/capital-flow/detail', method: 'GET', params })
  }
}

export const systemApi = {
  health() {
    return request({ url: '/system/health', method: 'GET' })
  },
  status() {
    return request({ url: '/system/status', method: 'GET' })
  },
  clearCache() {
    return request({ url: '/system/cache/clear', method: 'POST' })
  },
  collectionStatus() {
    return request({ url: '/system/collection-status', method: 'GET' })
  },
  sourceHealth() {
    return request({ url: '/system/source-health', method: 'GET' })
  }
}

export default { initApi, getApiClient, request, dashboardApi, systemApi }
