import { defineStore } from 'pinia'
import { ref, computed, shallowRef } from 'vue'
import { dashboardApi } from '@/core/api.js'
import { wsClient } from '@/core/websocket.js'
import { SECTOR_NAMES } from '@/core/constants.js'

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const error = ref('')
  const overviewData = shallowRef(null)
  const lineChartData = shallowRef(null)
  const sectorDetail = shallowRef(null)
  const lineChartError = ref(false)
  const wsConnected = ref(false)
  const lastRefreshTime = ref(null)
  let _wsUnsub = null
  let _wsConnectedUnsub = null
  let _wsDisconnectedUnsub = null

  let lineChartAbortController = null

  const avgIndex = computed(() => {
    const val = overviewData.value?.avg_index
    return val != null ? val : null
  })

  const sectorCount = computed(() => overviewData.value?.sector_count ?? 0)
  const validSectorCount = computed(() => overviewData.value?.valid_sector_count ?? 0)

  const sectors = computed(() => overviewData.value?.sectors ?? {})
  const degradedSectors = computed(() => overviewData.value?.degraded_sectors ?? [])
  const hasValidUserDiscussion = computed(() => overviewData.value?.has_valid_user_discussion ?? false)
  const lastUpdateTime = computed(() => overviewData.value?.last_update_time ?? null)
  const dataProvenance = computed(() => overviewData.value?.data_provenance ?? null)
  const dataQuality = computed(() => overviewData.value?.data_quality ?? null)
  const dataFreshness = computed(() => overviewData.value?.data_freshness ?? null)
  const isRealData = computed(() => overviewData.value?.is_real_data ?? false)

  const sectorList = computed(() => {
    const secs = sectors.value
    if (!secs) return []
    return Object.entries(secs)
      .filter(([_, data]) => {
        if (!data || data.index == null) return false
        const postCount = data.post_count || 0
        const buy = data.buy || 0
        const sell = data.sell || 0
        const isDegraded = data.is_degraded
        if (postCount === 0) return false
        if (data.index === 0 && buy === 0 && sell === 0) return false
        return true
      })
      .map(([code, data]) => ({
        code,
        name: data?.name || SECTOR_NAMES[code] || code,
        index: data.index,
        buy: data.buy || 0,
        sell: data.sell || 0,
        post_count: data.post_count || 0,
        positive_ratio: data.positive_ratio || 50,
        total: (data.buy || 0) + (data.sell || 0) || data.post_count || 0,
        ratio: (data.buy + data.sell) > 0 ? data.buy / (data.buy + data.sell) : (data.positive_ratio ? data.positive_ratio / 100 : 0.5),
        is_degraded: data.is_degraded || false
      }))
      .sort((a, b) => (b.index || 0) - (a.index || 0))
  })

  function _applyOverviewData(data) {
    if (!data) return
    overviewData.value = {
      avg_index: data.avg_index ?? null,
      sector_count: data.sector_count ?? 0,
      valid_sector_count: data.valid_sector_count ?? 0,
      last_update_time: data.last_update_time ?? null,
      sectors: data.sectors ?? {},
      degraded_sectors: data.degraded_sectors ?? [],
      has_valid_user_discussion: data.has_valid_user_discussion ?? false,
      is_real_data: data.is_real_data ?? false,
      data_provenance: data.data_provenance ?? null,
      data_quality: data.data_quality ?? null,
      data_freshness: data.data_freshness ?? null
    }
    error.value = ''
    lastRefreshTime.value = Date.now()
  }

  async function fetchOverview() {
    try {
      const res = await dashboardApi.getOverview()
      const data = res?.data
      if (res?.code === 200 && data) {
        _applyOverviewData(data)
      } else {
        throw new Error(res?.message || '返回数据为空')
      }
    } catch (e) {
      if (!wsConnected.value) {
        error.value = e?.userMessage || e?.message || '获取大盘概览失败'
      }
      throw e
    }
  }

  async function fetchLineChart(secs, days = 7) {
    if (lineChartAbortController) {
      lineChartAbortController.abort()
    }
    const controller = new AbortController()
    lineChartAbortController = controller
    lineChartError.value = false
    try {
      const res = await dashboardApi.getLineChart(secs, days, { signal: controller.signal })
      if (controller.signal.aborted) return
      const data = res?.data
      if (res?.code === 200 && data && data.series_data) {
        lineChartData.value = {
          x_axis: data.x_axis ?? [],
          legend: data.legend ?? [],
          series_data: data.series_data ?? []
        }
      } else {
        lineChartData.value = null
      }
    } catch (e) {
      if (controller.signal.aborted || e?.name === 'CanceledError') return
      lineChartError.value = true
      console.error('获取折线图数据失败:', e)
    } finally {
      if (lineChartAbortController === controller) {
        lineChartAbortController = null
      }
    }
  }

  async function fetchSectorDetail(code) {
    try {
      const res = await dashboardApi.getSectorDetail(code)
      if (res?.code === 200 && res?.data) {
        sectorDetail.value = res.data
      } else {
        sectorDetail.value = null
      }
    } catch (e) {
      sectorDetail.value = null
      console.error('获取板块详情失败:', e)
    }
  }

  async function fetchAll(secs, days = 7) {
    loading.value = true
    error.value = ''
    lineChartError.value = false
    try {
      await fetchOverview()
      await fetchLineChart(secs, days)
    } finally {
      loading.value = false
    }
  }

  function initWebSocket() {
    if (_wsUnsub) return
    _wsUnsub = wsClient.on('dashboard', (msg) => {
      const wrapped = msg?.data
      if (wrapped?.code === 200 && wrapped?.data) {
        _applyOverviewData(wrapped.data)
      }
    })
    _wsConnectedUnsub = wsClient.on('connected', () => {
      wsConnected.value = true
      error.value = ''
    })
    _wsDisconnectedUnsub = wsClient.on('disconnected', () => {
      wsConnected.value = false
    })
    if (!wsClient.isConnected()) {
      wsClient.init()
    } else {
      wsConnected.value = true
    }
  }

  function closeWebSocket() {
    if (_wsUnsub) {
      _wsUnsub()
      _wsUnsub = null
    }
    if (_wsConnectedUnsub) {
      _wsConnectedUnsub()
      _wsConnectedUnsub = null
    }
    if (_wsDisconnectedUnsub) {
      _wsDisconnectedUnsub()
      _wsDisconnectedUnsub = null
    }
    wsConnected.value = false
  }

  function clearError() {
    error.value = ''
    lineChartError.value = false
  }

  return {
    loading, error,
    overviewData, lineChartData, sectorDetail,
    lineChartError, wsConnected,
    lastRefreshTime,
    avgIndex, sectorCount, validSectorCount,
    sectors, degradedSectors, hasValidUserDiscussion, isRealData,
    lastUpdateTime, dataProvenance, dataQuality, dataFreshness,
    sectorList,
    fetchOverview, fetchLineChart, fetchSectorDetail, fetchAll,
    initWebSocket, closeWebSocket,
    clearError
  }
})
