<template>
  <div class="dashboard-view ios-animate-fade">
    <div class="dashboard-container">
      <header class="dashboard-header">
        <div class="header-left">
          <h1 class="page-title">数据看板</h1>
          <span v-if="lastUpdateTime" class="update-time">
            <span class="time-dot"></span>
            更新于 {{ formatTime(lastUpdateTime) }}
          </span>
        </div>
        <div class="header-right">
          <IOSSegmentControl v-model="timeRange" :options="timeOptions" @update:modelValue="handleTimeRangeChange" />
        </div>
      </header>

      <div v-if="loading && !overviewData" class="loading-state">
        <div class="ios-spinner"></div>
        <span class="loading-text">加载中...</span>
      </div>

      <div v-else-if="error" class="error-state">
        <span class="error-icon">{{ errorIcon }}</span>
        <p class="error-text">{{ error }}</p>
        <button class="ios-button ios-button-primary" @click="refreshData">重新加载</button>
      </div>

      <template v-else>
        <div class="metrics-grid">
          <IOSMetricCard
            title="综合情绪指数"
            :value="avgIndex"
            :subValue="indexChange"
            :color="indexColor"
            icon="📊"
            :trend="indexTrend"
          />
          <IOSMetricCard
            title="有效板块"
            :value="validSectorCount"
            :subValue="`/ ${sectorCount} 个板块`"
            color="blue"
            icon="📈"
          />
          <IOSMetricCard
            title="数据状态"
            value="正常"
            :subValue="dataQualityText"
            :color="dataQualityColor"
            icon="✅"
          />
        </div>

        <div class="chart-section ios-section">
          <div class="section-header">
            <h2 class="section-title">情绪走势</h2>
            <span class="section-subtitle">{{ chartSubtitle }}</span>
          </div>
          <IOSCard elevated>
            <IOSLineChart v-if="lineChartData" :data="lineChartData" height="440px" />
            <div v-else class="chart-placeholder">
              <span class="placeholder-text">暂无图表数据</span>
            </div>
          </IOSCard>
        </div>

        <div class="content-grid">
          <div class="sectors-section ios-section">
            <div class="section-header">
              <h2 class="section-title">板块排行</h2>
            </div>
            <IOSSectorList
              v-model="selectedSectors"
              :sectors="sectorRankingData"
              title=""
              @update:modelValue="handleSectorSelect"
            />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useSystemStore } from '@/stores/system'
import IOSMetricCard from '@/components/ios/IOSMetricCard.vue'
import IOSCard from '@/components/ios/IOSCard.vue'
import IOSLineChart from '@/components/ios/IOSLineChart.vue'
import IOSSectorList from '@/components/ios/IOSSectorList.vue'
import IOSSegmentControl from '@/components/ios/IOSSegmentControl.vue'
import { SECTOR_NAMES, SECTOR_COLORS, SECTOR_CATEGORIES } from '@/core/constants'

const store = useDashboardStore()
const systemStore = useSystemStore()

const timeRange = ref('近7天')
const timeOptions = ['近7天', '近30天', '近90天']
const timeRangeDays = { '近7天': 7, '近30天': 30, '近90天': 90 }

const allLeafSectorCodes = computed(() => {
  const codes = []
  SECTOR_CATEGORIES.forEach(cat => codes.push(...cat.children))
  return codes
})

const selectedSectors = ref([...allLeafSectorCodes.value])
let refreshTimer = null

const loading = computed(() => store.loading)
const error = computed(() => {
  // 网络断开时优先显示网络错误，而非API错误
  if (!systemStore.isOnline) {
    return '网络连接已断开，请检查网络连接'
  }
  return store.error
})
const errorIcon = computed(() => {
  if (!systemStore.isOnline) return '📡'
  return '⚠️'
})
const overviewData = computed(() => store.overviewData)
const lineChartData = computed(() => store.lineChartData)

const avgIndex = computed(() => overviewData.value?.avg_index ?? null)
const sectorCount = computed(() => overviewData.value?.sector_count ?? 0)
const validSectorCount = computed(() => overviewData.value?.valid_sector_count ?? 0)
const lastUpdateTime = computed(() => overviewData.value?.last_update_time ?? null)
const dataQuality = computed(() => overviewData.value?.data_quality ?? null)

const indexChange = computed(() => {
  return null
})

const indexColor = computed(() => {
  const val = avgIndex.value
  if (val == null) return null
  if (val >= 60) return 'red'
  if (val >= 40) return 'orange'
  if (val >= 20) return 'blue'
  return 'gray'
})

const indexTrend = computed(() => {
  return 'flat'
})

const dataQualityText = computed(() => {
  if (!dataQuality.value) return '实时更新'
  const dq = dataQuality.value
  if (dq.available === false) return dq.reason || '数据校验中'
  const marketIssues = dq.market_data?.issues?.length || 0
  const capitalIssues = dq.capital_flow?.issues?.length || 0
  if (marketIssues === 0 && capitalIssues === 0) return '数据校验通过'
  return `${marketIssues + capitalIssues} 个待处理项`
})

const dataQualityColor = computed(() => {
  if (!dataQuality.value) return 'green'
  const dq = dataQuality.value
  if (dq.available === false) return 'orange'
  const marketIssues = dq.market_data?.issues?.length || 0
  const capitalIssues = dq.capital_flow?.issues?.length || 0
  if (marketIssues === 0 && capitalIssues === 0) return 'green'
  return 'orange'
})

const sectorRankingData = computed(() => {
  const sectors = overviewData.value?.sectors
  if (!sectors) return []
  return Object.entries(sectors)
    .map(([code, data]) => {
      const idx = data?.index
      return {
        code,
        name: SECTOR_NAMES[code] || code,
        value: idx,
        color: SECTOR_COLORS[code] || '#007AFF'
      }
    })
    .filter(s => s.value != null)
    .sort((a, b) => (b.value || 0) - (a.value || 0))
})

const chartSubtitle = computed(() => {
  const count = selectedSectors.value.length
  const total = allLeafSectorCodes.value.length
  if (count === 0 || count === total) return `全部板块（${total}）`
  return `已选 ${count} 个板块`
})

function formatTime(timeStr) {
  if (!timeStr) return '--'
  try {
    const date = new Date(timeStr)
    if (isNaN(date.getTime())) return timeStr
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return timeStr
  }
}

async function fetchData() {
  // 网络断开时不发起请求，避免无意义的超时等待
  if (!systemStore.isOnline) {
    return
  }
  try {
    const days = timeRangeDays[timeRange.value] || 7
    await store.fetchAll(selectedSectors.value, days)
  } catch (e) {
    console.error('数据加载失败:', e)
  }
}

async function refreshLineChart() {
  try {
    const days = timeRangeDays[timeRange.value] || 7
    await store.fetchLineChart(selectedSectors.value, days)
  } catch (e) {
    console.error('折线图加载失败:', e)
  }
}

function refreshData() {
  fetchData()
}

function handleTimeRangeChange() {
  refreshLineChart()
}

function handleSectorSelect() {
  refreshLineChart()
}

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = setInterval(() => {
    fetchData()
  }, 30000)
}

onMounted(() => {
  fetchData()
  startAutoRefresh()
})

// 网络恢复后自动重新加载数据
watch(() => systemStore.isOnline, (online) => {
  if (online && !overviewData.value) {
    fetchData()
  }
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard-view {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  @include ios-scrollbar;
  @include ios-safe-bottom;
}

.dashboard-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--ios-spacing-xl) var(--ios-spacing-lg);
  padding-top: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px) + var(--ios-spacing-xl));

  @include mobile {
    padding: var(--ios-spacing-lg) var(--ios-spacing-md);
    padding-top: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px) + var(--ios-spacing-lg));
  }
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ios-spacing-xl);
  gap: var(--ios-spacing-lg);
  flex-wrap: wrap;

  @include mobile {
    flex-direction: column;
    align-items: stretch;
    gap: var(--ios-spacing-md);
    margin-bottom: var(--ios-spacing-lg);
  }
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-md);
}

.page-title {
  font-size: var(--ios-text-3xl);
  font-weight: 700;
  color: var(--ios-label-primary);
  letter-spacing: -0.02em;
}

.update-time {
  display: inline-flex;
  align-items: center;
  gap: var(--ios-spacing-xs);
  font-size: var(--ios-text-sm);
  color: var(--ios-label-secondary);
}

.time-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--ios-green);
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.header-right {
  flex-shrink: 0;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ios-spacing-3xl) var(--ios-spacing-lg);
  gap: var(--ios-spacing-lg);
}

.loading-text {
  font-size: var(--ios-text-base);
  color: var(--ios-label-secondary);
}

.error-icon {
  font-size: 48px;
}

.error-text {
  font-size: var(--ios-text-base);
  color: var(--ios-label-secondary);
  text-align: center;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--ios-spacing-lg);
  margin-bottom: var(--ios-spacing-xl);

  @include mobile {
    grid-template-columns: 1fr;
    gap: var(--ios-spacing-md);
    margin-bottom: var(--ios-spacing-lg);
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ios-spacing-md);
}

.section-title {
  font-size: var(--ios-text-lg);
  font-weight: 600;
  color: var(--ios-label-primary);
}

.section-subtitle {
  font-size: var(--ios-text-sm);
  color: var(--ios-label-secondary);
}

.chart-section {
  margin-bottom: var(--ios-spacing-xl);

  @include mobile {
    margin-bottom: var(--ios-spacing-lg);
  }
}

.chart-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 440px;
}

.placeholder-text {
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-base);
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--ios-spacing-lg);
}

.sectors-section {
  margin-bottom: var(--ios-spacing-xl);

  @include mobile {
    margin-bottom: var(--ios-spacing-lg);
  }
}

.ios-button {
  @include ios-button;
}

.ios-button-primary {
  @include ios-button-primary;
}
</style>
