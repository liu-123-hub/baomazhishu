/**
 * 三端通用API层 - 统一网络请求与错误处理
 */
import axios from 'axios'
import platform from '@/platform/core.js'
import { APP_CONFIG } from './constants.js'

let backendPort = 8000
let apiClient = null

function getApiBaseUrl() {
  if (platform.isElectron && window.electronAPI) {
    return `http://localhost:${backendPort}/api`
  }
  if (platform.isTauri && window.__TAURI__) {
    const tauriPort = window.__TAURI_BACKEND_PORT__ || 8000
    return `http://localhost:${tauriPort}/api`
  }
  return APP_CONFIG.apiBaseUrl
}

export async function initApi() {
  if (platform.isElectron && window.electronAPI) {
    try {
      const portInfo = await window.electronAPI.getBackendPort()
      backendPort = portInfo.port || 8000
      window.electronAPI.onBackendPort((info) => {
        backendPort = info.port || 8000
        updateApiClient()
      })
    } catch (e) {
      console.warn('[API] Failed to get Electron backend port:', e)
    }
  }
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
        // 区分"真实无网络"与"后端服务不可达"
        // navigator.onLine 反映浏览器/系统的网络连接状态
        // 为 true 时说明网络正常，是后端服务未启动或不可达
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
  return getApiClient()(config)
}

export const dashboardApi = {
  getOverview() {
    return request({ url: '/dashboard/overview', method: 'GET' })
  },
  getLineChart(sectors, days = 7) {
    const params = {}
    if (sectors) params.sectors = Array.isArray(sectors) ? sectors.join(',') : sectors
    if (days) params.days = days
    return request({ url: '/dashboard/line-chart', method: 'GET', params })
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
