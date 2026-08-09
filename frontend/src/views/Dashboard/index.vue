<template>
  <div class="dashboard-view ios-animate-fade">
    <div class="dashboard-container">
      <header class="dashboard-header" role="banner">
        <div class="header-left">
          <h1 class="page-title">数据看板</h1>
          <span v-if="lastUpdateTime" class="update-time" :aria-label="`更新于 ${formatTime(lastUpdateTime)}`">
            <span class="time-dot" :class="{ 'ws-connected': wsConnected }" :aria-hidden="true"></span>
            更新于 {{ formatTime(lastUpdateTime) }}
          </span>
        </div>
        <div class="header-right">
          <IOSSegmentControl
            v-model="timeRange"
            :options="timeOptions"
            aria-label="时间范围选择"
            @update:modelValue="handleTimeRangeChange"
          />
        </div>
      </header>

      <!-- 骨架屏加载状态 -->
      <template v-if="isInitialLoading">
        <div class="metrics-skeleton" aria-label="加载中">
          <IOSSkeleton v-for="i in 3" :key="i" variant="card" class="metric-skeleton-item" />
        </div>
        <div class="category-filter-skeleton">
          <div class="skeleton-block" style="width: 280px; height: 34px; border-radius: 10px;"></div>
        </div>
        <div class="chart-skeleton ios-section">
          <div class="section-header-skeleton">
            <div class="skeleton-block" style="width: 80px; height: 22px;"></div>
            <div class="skeleton-block" style="width: 100px; height: 16px;"></div>
          </div>
          <IOSSkeleton variant="chart" />
        </div>
        <div class="list-skeleton ios-section">
          <div class="section-header-skeleton">
            <div class="skeleton-block" style="width: 80px; height: 22px;"></div>
          </div>
          <IOSSkeleton variant="list" :rows="8" />
        </div>
      </template>

      <!-- 错误状态 -->
      <div v-else-if="hasError" class="error-state" role="alert" aria-live="assertive">
        <span class="error-icon" aria-hidden="true">{{ errorIcon }}</span>
        <p class="error-text">{{ errorMessage }}</p>
        <button
          class="ios-button ios-button-primary"
          @click="fetchData"
          :disabled="loading"
          aria-label="重新加载数据"
        >
          {{ loading ? '加载中...' : '重新加载' }}
        </button>
      </div>

      <!-- 正常内容 -->
      <template v-else>
        <!-- 指标卡片 -->
        <section class="metrics-section" aria-label="数据概览">
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
        </section>

        <!-- 分类筛选 -->
        <section class="category-filter" aria-label="板块分类筛选">
          <IOSSegmentControl
            v-model="selectedCategory"
            :options="categoryOptions"
            aria-label="板块分类"
            @update:modelValue="handleCategoryChange"
          />
        </section>

        <!-- 走势图 -->
        <section class="chart-section ios-section" aria-label="情绪走势图">
          <div class="section-header">
            <h2 class="section-title">情绪走势</h2>
            <span class="section-subtitle">{{ chartSubtitle }}</span>
            <button
              v-if="lineChartError"
              class="retry-btn"
              @click="refreshLineChart"
              aria-label="重新加载图表"
            >
              重试
            </button>
          </div>
          <IOSCard elevated>
            <div v-if="lineChartLoading" class="chart-loading">
              <div class="ios-spinner" aria-hidden="true"></div>
              <span class="loading-text">加载图表中...</span>
            </div>
            <IOSLineChart v-else-if="lineChartData" :data="lineChartData" height="440px" />
            <div v-else class="chart-placeholder">
              <span class="placeholder-icon" aria-hidden="true">📈</span>
              <span class="placeholder-text">
                {{ lineChartError ? '图表数据加载失败' : '暂无图表数据' }}
              </span>
              <button v-if="lineChartError" class="ios-button ios-button-secondary" @click="refreshLineChart">
                点击重试
              </button>
            </div>
          </IOSCard>
        </section>

        <!-- 板块排行 -->
        <section class="sectors-section ios-section" aria-label="板块排行">
          <div class="section-header">
            <h2 class="section-title">板块排行</h2>
            <span class="section-count" v-if="sectorRankingData.length">
              共 {{ sectorRankingData.length }} 个板块
            </span>
          </div>
          <IOSSectorList
            v-model="selectedSectors"
            :sectors="sectorRankingData"
            :navigable="true"
            title=""
            @update:modelValue="handleSectorSelect"
            @navigate="handleSectorNavigate"
          />
        </section>

        <!-- 离线下拉刷新提示（移动端） -->
        <div v-if="!systemStore.isOnline" class="offline-banner" role="status">
          <span aria-hidden="true">📡</span>
          <span>当前处于离线状态，数据可能不是最新</span>
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
import { useToastStore } from '@/stores/toast'
import IOSMetricCard from '@/components/ios/IOSMetricCard.vue'
import IOSCard from '@/components/ios/IOSCard.vue'
import IOSLineChart from '@/components/ios/IOSLineChart.vue'
import IOSSectorList from '@/components/ios/IOSSectorList.vue'
import IOSSegmentControl from '@/components/ios/IOSSegmentControl.vue'
import IOSSkeleton from '@/components/ios/IOSSkeleton.vue'
import { SECTOR_NAMES, SECTOR_COLORS, SECTOR_CATEGORIES, INDEX_LEVELS } from '@/core/constants'

const router = useRouter()
const store = useDashboardStore()
const systemStore = useSystemStore()
const toastStore = useToastStore()

const timeRange = ref('近7天')
const timeOptions = ['近7天', '近30天', '近90天']
const timeRangeDays = { '近7天': 7, '近30天': 30, '近90天': 90 }

const POLL_INTERVAL_WS = 120000
const POLL_INTERVAL_NO_WS = 30000
const LINE_CHART_REFRESH_INTERVAL = 60000

// 页面可见性变化防抖配置
const VISIBILITY_DEBOUNCE_MS = 1500 // 切回页面后等待1.5秒再刷新，避免快速切换
const MIN_HIDDEN_TIME_FOR_REFRESH = 30000 // 后台至少30秒才刷新，短时间切换不刷新

let visibilityTimer = null
let lastHiddenTime = 0

function handleVisibilityChange() {
  if (document.visibilityState === 'visible') {
    const hiddenDuration = Date.now() - lastHiddenTime
    // 后台时间太短，不刷新（避免频繁切换标签页导致的重复刷新）
    if (hiddenDuration < MIN_HIDDEN_TIME_FOR_REFRESH) {
      return
    }
    // 防抖：延迟刷新，避免快速来回切换
    if (visibilityTimer) {
      clearTimeout(visibilityTimer)
    }
    visibilityTimer = setTimeout(() => {
      if (document.visibilityState === 'visible' && systemStore.isOnline) {
        // 页面从后台切回时静默刷新，不打扰用户
        fetchData(true)
      }
    }, VISIBILITY_DEBOUNCE_MS)
  } else {
    // 页面隐藏时记录时间
    lastHiddenTime = Date.now()
    // 清除待执行的刷新
    if (visibilityTimer) {
      clearTimeout(visibilityTimer)
      visibilityTimer = null
    }
  }
}

const categoryOptions = computed(() => {
  return [
    { label: '全部', value: 'all' },
    ...SECTOR_CATEGORIES.map(cat => ({ label: cat.name.split('·')[0] || cat.name, value: cat.code }))
  ]
})
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

const selectedSectors = ref([])
let pollTimer = null
let lineChartTimer = null

const loading = computed(() => store.loading)
const lineChartLoading = computed(() => loading.value && !lineChartData.value)
const isInitialLoading = computed(() => loading.value && !overviewData.value)
const wsConnected = computed(() => store.wsConnected)

const errorMessage = computed(() => {
  if (!systemStore.isOnline) {
    return '网络连接已断开，请检查网络连接'
  }
  if (wsConnected.value) return ''
  return store.error
})

const hasError = computed(() => !!errorMessage.value)

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
  if (val >= INDEX_LEVELS.EXTREME_GREED.max) return 'red'
  if (val >= INDEX_LEVELS.GREED.max) return 'red'
  if (val >= INDEX_LEVELS.NEUTRAL.max) return 'orange'
  return 'blue'
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

async function fetchData(silent = false) {
  if (!systemStore.isOnline && !overviewData.value) {
    toastStore.warning('网络连接已断开')
    return
  }
  try {
    const days = timeRangeDays[timeRange.value] || 7
    await store.fetchAll(selectedSectors.value, days)
    // 静默模式不显示 toast，仅在有数据且非静默时显示
    if (overviewData.value && !silent) {
      toastStore.success('数据已更新')
    }
  } catch (e) {
    console.error('数据加载失败:', e)
  }
}

async function refreshOverview() {
  if (!systemStore.isOnline) return
  try {
    await store.fetchOverview()
  } catch (e) {
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

onMounted(() => {
  selectedSectors.value = [...allLeafSectorCodes.value]
  store.initWebSocket()
  fetchData()
  scheduleNextPoll()
  scheduleLineChartRefresh()
  document.addEventListener('visibilitychange', handleVisibilityChange)
})

watch(() => systemStore.isOnline, (online) => {
  if (online && !overviewData.value) {
    fetchData()
  }
})

watch(wsConnected, (connected) => {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = null
  }
  scheduleNextPoll()
  if (connected) {
    toastStore.success('实时连接已建立')
  }
})

watch(lastUpdateTime, (newTime, oldTime) => {
  if (newTime && newTime !== oldTime && oldTime) {
    // 静默更新，不每次都弹toast
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
  if (visibilityTimer) {
    clearTimeout(visibilityTimer)
    visibilityTimer = null
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

  @include tablet {
    padding: var(--ios-spacing-xl) var(--ios-spacing-lg);
    padding-top: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px) + var(--ios-spacing-xl));
  }

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

  @include tablet {
    margin-bottom: var(--ios-spacing-lg);
  }

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
  flex-wrap: wrap;
}

.page-title {
  font-size: var(--ios-text-3xl);
  font-weight: 700;
  color: var(--ios-label-primary);
  letter-spacing: -0.02em;
  margin: 0;

  @include mobile {
    font-size: var(--ios-text-2xl);
  }
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

  @include mobile {
    width: 100%;
  }
}

// Skeleton styles
.metrics-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--ios-spacing-lg);
  margin-bottom: var(--ios-spacing-lg);

  @include mobile {
    grid-template-columns: 1fr;
    gap: var(--ios-spacing-md);
  }
}

.metric-skeleton-item {
  background: transparent;
  padding: 0;
}

.category-filter-skeleton {
  display: flex;
  justify-content: center;
  margin-bottom: var(--ios-spacing-lg);
}

.chart-skeleton,
.list-skeleton {
  margin-bottom: var(--ios-spacing-xl);
}

.section-header-skeleton {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ios-spacing-md);
}

.skeleton-block {
  background: linear-gradient(
    90deg,
    var(--ios-fill-primary) 25%,
    var(--ios-fill-secondary) 50%,
    var(--ios-fill-primary) 75%
  );
  background-size: 200% 100%;
  border-radius: var(--ios-radius-sm);
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

// Loading/Error states
.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--ios-spacing-3xl) var(--ios-spacing-lg);
  gap: var(--ios-spacing-lg);
  min-height: 400px;
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
  max-width: 400px;
}

// Metrics
.metrics-section {
  margin-bottom: var(--ios-spacing-lg);

  @include mobile {
    margin-bottom: var(--ios-spacing-md);
  }
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: var(--ios-spacing-lg);

  @include tablet {
    grid-template-columns: repeat(3, 1fr);
  }

  @include mobile {
    grid-template-columns: 1fr;
    gap: var(--ios-spacing-md);
  }
}

// Category filter
.category-filter {
  display: flex;
  justify-content: center;
  margin-bottom: var(--ios-spacing-lg);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  @include ios-scrollbar;

  @include mobile {
    margin-bottom: var(--ios-spacing-md);
    justify-content: flex-start;

    :deep(.ios-segment-control) {
      min-width: max-content;
    }
  }
}

// Section header
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--ios-spacing-md);
  gap: var(--ios-spacing-md);
}

.section-title {
  font-size: var(--ios-text-lg);
  font-weight: 600;
  color: var(--ios-label-primary);
  margin: 0;
}

.section-subtitle,
.section-count {
  font-size: var(--ios-text-sm);
  color: var(--ios-label-secondary);
}

.retry-btn {
  font-size: var(--ios-text-sm);
  color: var(--ios-blue);
  font-weight: 500;
  padding: var(--ios-spacing-xs) var(--ios-spacing-sm);
  border-radius: var(--ios-radius-sm);
  background: var(--ios-fill-primary);
  transition: all var(--ios-duration-fast) var(--ios-ease);

  @media (hover: hover) {
    &:hover {
      background: var(--ios-fill-secondary);
    }
  }

  &:active {
    transform: scale(0.96);
  }
}

// Chart section
.chart-section {
  margin-bottom: var(--ios-spacing-xl);

  @include mobile {
    margin-bottom: var(--ios-spacing-lg);
  }
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 440px;
  gap: var(--ios-spacing-md);

  @include mobile {
    height: 320px;
  }
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 440px;
  gap: var(--ios-spacing-md);

  @include mobile {
    height: 320px;
  }
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.5;
}

.placeholder-text {
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-base);
}

// Sectors section
.sectors-section {
  margin-bottom: var(--ios-spacing-xl);

  @include mobile {
    margin-bottom: var(--ios-spacing-lg);
  }
}

// Offline banner
.offline-banner {
  position: fixed;
  bottom: calc(env(safe-area-inset-bottom, 0px) + var(--ios-spacing-lg));
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  padding: var(--ios-spacing-sm) var(--ios-spacing-lg);
  background: var(--ios-bg-elevated);
  border-radius: var(--ios-radius-full);
  box-shadow: var(--ios-shadow-lg);
  font-size: var(--ios-text-sm);
  font-weight: 500;
  color: var(--ios-label-primary);
  z-index: 100;
  animation: slideUp var(--ios-duration-normal) var(--ios-spring);

  @include mobile {
    bottom: calc(env(safe-area-inset-bottom, 0px) + var(--ios-spacing-md));
    font-size: var(--ios-text-xs);
    padding: var(--ios-spacing-xs) var(--ios-spacing-md);
  }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateX(-50%) translateY(20px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

.ios-button {
  @include ios-button;
}

.ios-button-primary {
  @include ios-button-primary;
}

.ios-button-secondary {
  @include ios-button-secondary;
}

@media (prefers-reduced-motion: reduce) {
  .time-dot {
    animation: none;
  }

  .skeleton-block {
    animation: none;
  }

  .offline-banner {
    animation: none;
  }
}
</style>
