import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  getDashboardOverview,
  getLineChartData,
  getSectorDetail
} from '@/api/index'

export const useDashboardStore = defineStore('dashboard', () => {
  const loading = ref(false)
  const error = ref('')
  const overviewData = ref(null)
  const lineChartData = ref(null)
  const sectorDetail = ref(null)
  const lineChartError = ref(false)

  const avgIndex = computed(() => {
    const val = overviewData.value?.avg_index
    return val != null ? val : 0
  })

  const sectorCount = computed(() => {
    return overviewData.value?.sector_count ?? 0
  })

  const sectors = computed(() => {
    return overviewData.value?.sectors ?? {}
  })

  const lastUpdateTime = computed(() => {
    return overviewData.value?.last_update_time ?? null
  })

  async function fetchOverview() {
    try {
      const res = await getDashboardOverview()
      const data = res?.data ?? res
      if (data) {
        overviewData.value = {
          avg_index: data.avg_index ?? 0,
          sector_count: data.sector_count ?? 0,
          last_update_time: data.last_update_time ?? null,
          sectors: data.sectors ?? {}
        }
        error.value = ''
      } else {
        throw new Error('返回数据为空')
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
      const data = res?.data ?? res
      if (data && data.series_data) {
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

  async function fetchAll(sectors, days = 7) {
    loading.value = true
    error.value = ''
    lineChartError.value = false

    const results = await Promise.allSettled([
      fetchOverview(),
      fetchLineChart(sectors, days)
    ])

    const errors = []
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        const labels = ['大盘概览', '折线图数据']
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
  }

  return {
    loading,
    error,
    overviewData,
    lineChartData,
    sectorDetail,
    lineChartError,
    avgIndex,
    sectorCount,
    sectors,
    lastUpdateTime,
    fetchOverview,
    fetchLineChart,
    fetchSectorDetail,
    fetchAll,
    clearError
  }
})
