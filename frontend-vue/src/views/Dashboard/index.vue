<template>
  <div class="dashboard-view ios-animate-fade">
    <div class="dashboard-container">
      <header class="dashboard-header">
        <div class="header-left">
          <h1 class="page-title">数据看板</h1>
          <span v-if="lastUpdateTime" class="update-time">
            <span class="time-dot" :class="{ 'ws-connected': wsConnected }"></span>
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

      <div v-else-if="error && !wsConnected" class="error-state">
        <span class="error-icon">{{ errorIcon }}</span>
        <p class="error-text">{{ error }}</p>
        <button class="ios-button ios-button-primary" @click="fetchData">重新加载</button>
      </div>

      <template v-else>
        <div class="metrics-grid">
          <IOSMetricCard
            title="综合情绪指数"
            :value="avgIndex"
            :color="indexColor"
            icon="📊"
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

        <div class="category-filter">
          <IOSSegmentControl v-model="selectedCategory" :options="categoryOptions" @update:modelValue="handleCategoryChange" />
        </div>

        <div class="chart-section ios-section">
          <div class="section-header">
            <h2 class="section-title">情绪走势</h2>
            <span class="section-subtitle">{{ chartSubtitle }}</span>
          </div>
          <IOSCard elevated>
            <IOSLineChart v-if="lineChartData" :data="lineChartData" height="440px" />
            <div v-else class="chart-placeholder">
              <span class="placeholder-text">
                {{ lineChartError ? '图表数据加载失败，将在下次刷新时重试' : '暂无图表数据' }}
              </span>
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
              :navigable="true"
              title=""
              @update:modelValue="handleSectorSelect"
              @navigate="handleSectorNavigate"
            />
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useSystemStore } from '@/stores/system'
import IOSMetricCard from '@/components/ios/IOSMetricCard.vue'
import IOSCard from '@/components/ios/IOSCard.vue'
import IOSLineChart from '@/components/ios/IOSLineChart.vue'
import IOSSectorList from '@/components/ios/IOSSectorList.vue'
import IOSSegmentControl from '@/components/ios/IOSSegmentControl.vue'
import { SECTOR_NAMES, SECTOR_COLORS, SECTOR_CATEGORIES } from '@/core/constants'

const router = useRouter()
const store = useDashboardStore()
const systemStore = useSystemStore()

const timeRange = ref('近7天')
const timeOptions = ['近7天', '近30天', '近90天']
const timeRangeDays = { '近7天': 7, '近30天': 30, '近90天': 90 }

const POLL_INTERVAL_WS = 120000
const POLL_INTERVAL_NO_WS = 30000
const LINE_CHART_REFRESH_INTERVAL = 60000

const categoryOptions = [
  { label: '全部', value: 'all' },
  { label: '大金融', value: 'finance' },
  { label: '大消费', value: 'consumption' },
  { label: '大科技', value: 'technology' },
  { label: '大周期', value: 'cyclical' },
  { label: '其他', value: 'others' }
]
const selectedCategory = ref('all')

const allLeafSectorCodes = computed(() => {
  const codes = []
  SECTOR_CATEGORIES.forEach(cat => codes.push(...cat.children))
  return codes
})

const categorySectorCodes = computed(() => {
  if (selectedCategory.value === 'all') return allLeafSectorCodes.value
  const cat = SECTOR_CATEGORIES.find(c => c.code === selectedCategory.value)
  return cat ? cat.children : []
})

const selectedSectors = ref([...allLeafSectorCodes.value])
let pollTimer = null
let lineChartTimer = null

const loading = computed(() => store.loading)
const wsConnected = computed(() => store.wsConnected)
const error = computed(() => {
  if (!systemStore.isOnline) {
    return '网络连接已断开，请检查网络连接'
  }
  if (wsConnected.value) return ''
  return store.error
})
const errorIcon = computed(() => {
  if (!systemStore.isOnline) return '📡'
  return '⚠️'
})
const overviewData = computed(() => store.overviewData)
const lineChartData = computed(() => store.lineChartData)
const lineChartError = computed(() => store.lineChartError)

const avgIndex = computed(() => overviewData.value?.avg_index ?? null)
const sectorCount = computed(() => overviewData.value?.sector_count ?? 0)
const validSectorCount = computed(() => overviewData.value?.valid_sector_count ?? 0)
const lastUpdateTime = computed(() => overviewData.value?.last_update_time ?? null)
const dataQuality = computed(() => overviewData.value?.data_quality ?? null)

const indexColor = computed(() => {
  const val = avgIndex.value
  if (val == null) return null
  if (val >= 60) return 'red'
  if (val >= 40) return 'orange'
  if (val >= 20) return 'blue'
  return 'gray'
})

const dataQualityText = computed(() => {
  if (!dataQuality.value) return wsConnected.value ? '实时推送' : '实时更新'
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
  const allowedCodes = new Set(categorySectorCodes.value)
  return Object.entries(sectors)
    .filter(([code]) => allowedCodes.has(code))
    .map(([code, data]) => {
      const idx = data?.index
      return {
        code,
        name: data?.name || SECTOR_NAMES[code] || code,
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

async function refreshOverview() {
  if (!systemStore.isOnline) return
  try {
    await store.fetchOverview()
  } catch (e) {
    // WebSocket连接时不显示HTTP错误
    if (!wsConnected.value) {
      console.error('概览刷新失败:', e)
    }
  }
}

async function refreshLineChart() {
  if (!systemStore.isOnline) return
  try {
    const days = timeRangeDays[timeRange.value] || 7
    await store.fetchLineChart(selectedSectors.value, days)
  } catch (e) {
    console.error('折线图加载失败:', e)
  }
}

function handleTimeRangeChange() {
  refreshLineChart()
}

function handleCategoryChange() {
  selectedSectors.value = [...categorySectorCodes.value]
  refreshLineChart()
}

function handleSectorSelect() {
  refreshLineChart()
}

function handleSectorNavigate(sector) {
  if (sector?.code) {
    router.push(`/sector/${sector.code}`)
  }
}

function scheduleNextPoll() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  const interval = wsConnected.value ? POLL_INTERVAL_WS : POLL_INTERVAL_NO_WS
  pollTimer = setTimeout(async () => {
    if (document.visibilityState === 'visible') {
      await refreshOverview()
    }
    scheduleNextPoll()
  }, interval)
}

function scheduleLineChartRefresh() {
  if (lineChartTimer) {
    clearTimeout(lineChartTimer)
    lineChartTimer = null
  }
  lineChartTimer = setTimeout(async () => {
    if (document.visibilityState === 'visible' && systemStore.isOnline) {
      await refreshLineChart()
    }
    scheduleLineChartRefresh()
  }, LINE_CHART_REFRESH_INTERVAL)
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible' && systemStore.isOnline) {
    fetchData()
  }
}

onMounted(() => {
  store.initWebSocket()
  fetchData()
  scheduleNextPoll()
  scheduleLineChartRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

watch(() => systemStore.isOnline, (online) => {
  if (online) {
    fetchData()
  }
})

watch(wsConnected, (connected) => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  scheduleNextPoll()
})

// 监听概览数据更新时间变化：当WebSocket推送新数据导致lastUpdateTime改变时，自动刷新折线图
watch(lastUpdateTime, (newTime, oldTime) => {
  if (newTime && newTime !== oldTime) {
    refreshLineChart()
  }
})

onUnmounted(() => {
  store.closeWebSocket()
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  if (lineChartTimer) {
    clearTimeout(lineChartTimer)
    lineChartTimer = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
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

  &.ws-connected {
    background: #007aff;
    box-shadow: 0 0 6px rgba(0, 122, 255, 0.5);
  }
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
  margin-bottom: var(--ios-spacing-lg);

  @include mobile {
    grid-template-columns: 1fr;
    gap: var(--ios-spacing-md);
    margin-bottom: var(--ios-spacing-md);
  }
}

.category-filter {
  display: flex;
  justify-content: center;
  margin-bottom: var(--ios-spacing-lg);

  @include mobile {
    margin-bottom: var(--ios-spacing-md);
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
