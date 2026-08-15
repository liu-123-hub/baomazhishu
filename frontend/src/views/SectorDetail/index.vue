<template>
  <div class="sector-detail-view ios-animate-fade">
    <div class="detail-container">
      
      <template v-if="loading && !detail">
        <div class="detail-skeleton">
          <div class="sector-header-skeleton">
            <div class="skeleton-block" style="width: 120px; height: 28px; margin: 0 auto;"></div>
            <div class="skeleton-block" style="width: 140px; height: 70px; margin: 16px auto 0; border-radius: 16px;"></div>
          </div>
          <div class="metrics-grid-skeleton">
            <IOSSkeleton v-for="i in 4" :key="i" variant="card" />
          </div>
          <div class="info-skeleton ios-section">
            <IOSSkeleton variant="list" :rows="3" />
          </div>
          <div class="chart-skeleton ios-section">
            <div class="section-header-skeleton">
              <div class="skeleton-block" style="width: 80px; height: 22px;"></div>
            </div>
            <IOSSkeleton variant="chart" />
          </div>
        </div>
      </template>

      <!-- 错误状态 -->
      <div v-else-if="error" class="error-state" role="alert" aria-live="assertive">
        <span class="error-icon" aria-hidden="true">⚠️</span>
        <p class="error-text">{{ error }}</p>
        <button
          class="ios-button ios-button-primary"
          @click="fetchDetail"
          :disabled="loading"
          aria-label="重新加载板块详情"
        >
          {{ loading ? '加载中...' : '重新加载' }}
        </button>
      </div>

      <!-- 详情内容 -->
      <template v-else-if="detail">
        <header class="sector-header" role="banner">
          <div class="sector-title-row">
            <span class="sector-dot" :style="{ backgroundColor: sectorColor }" aria-hidden="true"></span>
            <h1 class="sector-name">{{ sectorName }}</h1>
          </div>
          <div class="index-display" :class="indexLevel" :aria-label="`情绪指数 ${displayIndex}，${indexLabel}`">
            <span class="index-value" aria-hidden="true">{{ displayIndex }}</span>
            <span class="index-label">{{ indexLabel }}</span>
          </div>
        </header>

        <section class="metrics-section" aria-label="板块数据指标">
          <div class="metrics-grid">
            <IOSMetricCard
              title="讨论帖数"
              :value="detail.post_count"
              color="blue"
              icon="💬"
            />
            <IOSMetricCard
              title="看涨情绪"
              :value="detail.buy"
              color="red"
              icon="📈"
            />
            <IOSMetricCard
              title="看跌情绪"
              :value="detail.sell"
              color="green"
              icon="📉"
            />
            <IOSMetricCard
              title="多头占比"
              :value="detail.positive_ratio"
              :subValue="'%'"
              :color="ratioColor"
              icon="⚖️"
            />
          </div>
        </section>

        <section class="info-card ios-section" aria-label="板块信息">
          <IOSCard elevated>
            <div class="info-row">
              <span class="info-label">情绪趋势</span>
              <span class="info-value" :class="trendClass">
                <span :aria-hidden="true">{{ trendIcon }}</span>
                {{ trendText }}
              </span>
            </div>
            <div class="info-row">
              <span class="info-label">数据状态</span>
              <span class="info-value" :class="{ degraded: detail.is_degraded }">
                {{ detail.is_degraded ? '降级数据' : '正常' }}
              </span>
            </div>
            <div class="info-row" v-if="detail.update_time">
              <span class="info-label">更新时间</span>
              <span class="info-value">{{ formatTime(detail.update_time) }}</span>
            </div>
          </IOSCard>
        </section>

        <section class="chart-section ios-section" aria-label="历史走势图">
          <div class="section-header">
            <h2 class="section-title">历史走势</h2>
            <button
              v-if="historyError"
              class="retry-btn"
              @click="() => fetchHistory(sectorCode, 30)"
              aria-label="重新加载历史数据"
            >
              重试
            </button>
          </div>
          <IOSCard elevated>
            <div v-if="loading && !historyData" class="chart-loading">
              <div class="ios-spinner" aria-hidden="true"></div>
              <span class="loading-text">加载历史数据...</span>
            </div>
            <IOSLineChart v-else-if="historyData" :data="historyData" height="320px" />
            <div v-else class="chart-placeholder">
              <span class="placeholder-icon" aria-hidden="true">📊</span>
              <span class="placeholder-text">
                {{ historyError ? '历史数据加载失败' : '暂无历史数据' }}
              </span>
              <button v-if="historyError" class="ios-button ios-button-secondary" @click="() => fetchHistory(sectorCode, 30)">
                点击重试
              </button>
            </div>
          </IOSCard>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { dashboardApi } from '@/core/api'
import IOSMetricCard from '@/components/ios/IOSMetricCard.vue'
import IOSCard from '@/components/ios/IOSCard.vue'
import IOSLineChart from '@/components/ios/IOSLineChart.vue'
import IOSSkeleton from '@/components/ios/IOSSkeleton.vue'
import { SECTOR_NAMES, SECTOR_COLORS } from '@/core/constants'

const route = useRoute()
const store = useDashboardStore()

const loading = ref(true)
const error = ref('')
const detail = ref(null)
const historyData = ref(null)
const historyError = ref(false)
let _historyRequestId = 0

const sectorCode = computed(() => route.params.code)
const sectorName = computed(() => detail.value?.name || SECTOR_NAMES[sectorCode.value] || sectorCode.value)
const sectorColor = computed(() => SECTOR_COLORS[sectorCode.value] || '#007AFF')

const displayIndex = computed(() => {
  const val = detail.value?.index
  return val != null ? val.toFixed(1) : '--'
})

const indexLevel = computed(() => {
  const val = detail.value?.index
  if (val == null) return 'neutral'
  if (val >= 60) return 'hot'
  if (val >= 40) return 'warm'
  if (val >= 20) return 'cool'
  return 'cold'
})

const indexLabel = computed(() => {
  const val = detail.value?.index
  if (val == null) return '暂无数据'
  if (val >= 80) return '极度贪婪'
  if (val >= 60) return '贪婪'
  if (val >= 40) return '中性'
  if (val >= 20) return '恐慌'
  return '极度恐慌'
})

const ratioColor = computed(() => {
  const val = detail.value?.positive_ratio
  if (val == null) return null
  if (val >= 60) return 'red'
  if (val >= 40) return 'orange'
  return 'blue'
})

const trendText = computed(() => detail.value?.trend || '平稳')
const trendIcon = computed(() => {
  const t = detail.value?.trend
  if (t === '上涨') return '↑ '
  if (t === '下跌') return '↓ '
  return '→ '
})
const trendClass = computed(() => {
  const t = detail.value?.trend
  if (t === '上涨') return 'trend-up'
  if (t === '下跌') return 'trend-down'
  return 'trend-flat'
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

async function fetchDetail() {
  const code = sectorCode.value
  if (!code) return
  loading.value = true
  error.value = ''
  historyError.value = false
  historyData.value = null
  _historyRequestId++
  try {
    await store.fetchSectorDetail(code)
    detail.value = store.sectorDetail
    if (!detail.value) {
      error.value = '未找到该板块数据'
    } else {
      await fetchHistory(code, 30)
    }
  } catch (e) {
    error.value = e?.userMessage || e?.message || '加载板块详情失败'
  } finally {
    loading.value = false
  }
}

async function fetchHistory(code, days = 30) {
  const requestId = ++_historyRequestId
  historyError.value = false
  try {
    const res = await dashboardApi.getLineChart([code], days)
    if (requestId !== _historyRequestId) return
    if (res?.code === 200 && res?.data?.series_data?.length) {
      historyData.value = {
        x_axis: res.data.x_axis ?? [],
        legend: res.data.legend ?? [sectorName.value],
        series_data: res.data.series_data
      }
    } else {
      historyError.value = true
    }
  } catch (e) {
    if (requestId !== _historyRequestId) return
    historyError.value = true
    console.error('获取历史数据失败:', e)
  }
}

watch(sectorCode, () => {
  fetchDetail()
})

onMounted(() => {
  fetchDetail()
})

onUnmounted(() => {
  _historyRequestId++
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.sector-detail-view {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  -webkit-overflow-scrolling: touch;
  @include ios-scrollbar;
  @include ios-safe-bottom;
}

.detail-container {
  max-width: 800px;
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


.detail-skeleton {
  .sector-header-skeleton {
    text-align: center;
    margin-bottom: var(--ios-spacing-xl);
    padding: var(--ios-spacing-xl) 0;
  }

  .metrics-grid-skeleton {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--ios-spacing-md);
    margin-bottom: var(--ios-spacing-lg);

    @include mobile {
      gap: var(--ios-spacing-sm);
    }
  }

  .info-skeleton,
  .chart-skeleton {
    margin-bottom: var(--ios-spacing-lg);
  }

  .section-header-skeleton {
    margin-bottom: var(--ios-spacing-md);
  }
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


.sector-header {
  text-align: center;
  margin-bottom: var(--ios-spacing-xl);
  padding: var(--ios-spacing-xl) 0;
}

.sector-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--ios-spacing-sm);
  margin-bottom: var(--ios-spacing-lg);
}

.sector-dot {
  width: 14px;
  height: 14px;
  border-radius: 50%;
}

.sector-name {
  font-size: var(--ios-text-2xl);
  font-weight: 700;
  color: var(--ios-label-primary);
  letter-spacing: -0.02em;
  margin: 0;
}

.index-display {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  padding: var(--ios-spacing-lg) var(--ios-spacing-2xl);
  border-radius: var(--ios-radius-xl);
  transition: background var(--ios-duration-normal) var(--ios-ease);

  &.hot {
    background: rgba(255, 59, 48, 0.1);
    .index-value { color: var(--ios-red); }
  }
  &.warm {
    background: rgba(255, 149, 0, 0.1);
    .index-value { color: var(--ios-orange); }
  }
  &.cool {
    background: rgba(0, 122, 255, 0.1);
    .index-value { color: var(--ios-blue); }
  }
  &.cold {
    background: var(--ios-fill-primary);
    .index-value { color: var(--ios-label-secondary); }
  }
  &.neutral {
    background: var(--ios-fill-primary);
    .index-value { color: var(--ios-label-secondary); }
  }

  :root.dark &, [data-theme="dark"] & {
    &.hot { background: rgba(255, 69, 58, 0.15); }
    &.warm { background: rgba(255, 159, 10, 0.15); }
    &.cool { background: rgba(10, 132, 255, 0.15); }
  }
}

.index-value {
  font-size: 56px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  line-height: 1;

  @include tablet {
    font-size: 52px;
  }

  @include mobile {
    font-size: 44px;
  }
}

.index-label {
  font-size: var(--ios-text-sm);
  color: var(--ios-label-secondary);
  margin-top: var(--ios-spacing-xs);
}


.metrics-section {
  margin-bottom: var(--ios-spacing-lg);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--ios-spacing-md);
  margin-bottom: var(--ios-spacing-lg);

  @include tablet {
    grid-template-columns: repeat(4, 1fr);
  }

  @include mobile {
    gap: var(--ios-spacing-sm);
  }
}


.info-card {
  margin-bottom: var(--ios-spacing-lg);
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--ios-spacing-md) 0;
  border-bottom: 1px solid var(--ios-separator);

  &:last-child {
    border-bottom: none;
  }
}

.info-label {
  font-size: var(--ios-text-base);
  color: var(--ios-label-secondary);
}

.info-value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--ios-text-base);
  font-weight: 500;
  color: var(--ios-label-primary);
  font-variant-numeric: tabular-nums;

  &.degraded { color: var(--ios-orange); }
  &.trend-up { color: var(--ios-red); }
  &.trend-down { color: var(--ios-green); }
  &.trend-flat { color: var(--ios-label-secondary); }
}


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


.chart-section {
  margin-bottom: var(--ios-spacing-xl);
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 320px;
  gap: var(--ios-spacing-md);
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 320px;
  gap: var(--ios-spacing-md);
}

.placeholder-icon {
  font-size: 48px;
  opacity: 0.5;
}

.placeholder-text {
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-base);
}


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
  .skeleton-block {
    animation: none;
  }
}
</style>
