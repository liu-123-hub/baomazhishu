import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getDashboardOverview,
  getLineChartData,
  getSectorDetail,
  getMarketData,
  getCapitalFlowSummary
} from '@/api/index'

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const error = ref('')
  const overviewData = ref(null)
  const lineChartData = ref(null)
  const sectorDetail = ref(null)
  const lineChartError = ref(false)
  const marketData = ref(null)
  const capitalFlowData = ref(null)
  const marketDataError = ref(false)
  const capitalFlowError = ref(false)

  const avgIndex = computed(() => {
    const val = overviewData.value?.avg_index
    return val != null ? val : null
  })

  const sectorCount = computed(() => {
    return overviewData.value?.sector_count ?? 0
  })

  const validSectorCount = computed(() => {
    return overviewData.value?.valid_sector_count ?? 0
  })

  const sectors = computed(() => {
    return overviewData.value?.sectors ?? {}
  })

  const degradedSectors = computed(() => {
    return overviewData.value?.degraded_sectors ?? []
  })

  const hasValidUserDiscussion = computed(() => {
    return overviewData.value?.has_valid_user_discussion ?? false
  })

  const lastUpdateTime = computed(() => {
    return overviewData.value?.last_update_time ?? null
  })

  const dataProvenance = computed(() => overviewData.value?.data_provenance ?? null)
  const dataQuality = computed(() => overviewData.value?.data_quality ?? null)
  const dataFreshness = computed(() => overviewData.value?.data_freshness ?? null)

  async function fetchOverview() {
    try {
      const res = await getDashboardOverview()
      const data = res?.data
      if (res?.code === 200 && data) {
        overviewData.value = {
          avg_index: data.avg_index ?? null,
          sector_count: data.sector_count ?? 0,
          valid_sector_count: data.valid_sector_count ?? 0,
          last_update_time: data.last_update_time ?? null,
          sectors: data.sectors ?? {},
          degraded_sectors: data.degraded_sectors ?? [],
          has_valid_user_discussion: data.has_valid_user_discussion ?? false,
          data_provenance: data.data_provenance ?? null,
          data_quality: data.data_quality ?? null,
          data_freshness: data.data_freshness ?? null
        }
        error.value = ''
      } else {
        throw new Error(res?.message || '返回数据为空')
      }
    } catch (e) {
      const msg = e?.message || '获取大盘概览失败'
      error.value = msg
      console.error(msg, e)
      throw e
    }
  }

  async function fetchLineChart(sectors, days = 7) {
    lineChartError.value = false
    try {
      const sectorStr = Array.isArray(sectors) ? sectors.join(',') : sectors
      const res = await getLineChartData(sectorStr, days)
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
      lineChartError.value = true
      const msg = e?.message || '获取折线图数据失败'
      console.error(msg, e)
      throw e
    }
  }

  async function fetchSectorDetail(code) {
    try {
      const res = await getSectorDetail(code)
      if (res.code === 200 && res.data) {
        sectorDetail.value = res.data
      } else {
        sectorDetail.value = null
      }
    } catch (e) {
      sectorDetail.value = null
      console.error('获取板块详情失败:', e)
      throw e
    }
  }

  async function fetchMarketData(sector) {
    marketDataError.value = false
    try {
      const res = await getMarketData(sector)
      const data = res?.data
      if (res?.code === 200 && data) {
        marketData.value = data
      } else {
        marketData.value = null
      }
    } catch (e) {
      marketDataError.value = true
      marketData.value = null
      console.error('获取行情数据失败:', e)
    }
  }

  async function fetchCapitalFlow() {
    capitalFlowError.value = false
    try {
      const res = await getCapitalFlowSummary()
      const data = res?.data
      if (res?.code === 200 && data) {
        capitalFlowData.value = data
      } else {
        capitalFlowData.value = null
      }
    } catch (e) {
      capitalFlowError.value = true
      capitalFlowData.value = null
      console.error('获取资金流向数据失败:', e)
    }
  }

  async function fetchAll(sectors, days = 7) {
    loading.value = true
    error.value = ''
    lineChartError.value = false

    const results = await Promise.allSettled([
      fetchOverview(),
      fetchLineChart(sectors, days),
      fetchMarketData(),
      fetchCapitalFlow()
    ])

    const errors = []
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        const labels = ['大盘概览', '折线图数据', '行情数据', '资金流向']
        errors.push(`${labels[index]}: ${result.reason?.message || '加载失败'}`)
      }
    })

    if (errors.length > 0) {
      error.value = errors.join('; ')
    }

    loading.value = false
  }

  function clearError() {
    error.value = ''
    lineChartError.value = false
    marketDataError.value = false
    capitalFlowError.value = false
  }

  return {
    loading,
    error,
    overviewData,
    lineChartData,
    sectorDetail,
    lineChartError,
    marketData,
    capitalFlowData,
    marketDataError,
    capitalFlowError,
    avgIndex,
    sectorCount,
    validSectorCount,
    sectors,
    degradedSectors,
    hasValidUserDiscussion,
    lastUpdateTime,
    dataProvenance,
    dataQuality,
    dataFreshness,
    fetchOverview,
    fetchLineChart,
    fetchSectorDetail,
    fetchMarketData,
    fetchCapitalFlow,
    fetchAll,
    clearError
  }
})
