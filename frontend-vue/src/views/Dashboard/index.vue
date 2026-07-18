<template>
  <div class="dashboard-page">
    <!-- 页面工具栏 -->
    <header class="dashboard-toolbar">
      <div class="toolbar-left">
        <h1 class="page-title">数据大屏</h1>
        <span class="update-time" v-if="overviewData?.last_update_time">
          <span class="time-dot pulse"></span>
          更新于 {{ formatTime(overviewData.last_update_time) }}
        </span>
      </div>
      <div class="toolbar-right">
        <el-radio-group
          v-model="timeRange"
          size="small"
          @change="handleTimeRangeChange"
          class="time-range-group"
        >
          <el-radio-button value="7d">近7天</el-radio-button>
          <el-radio-button value="30d">近30天</el-radio-button>
          <el-radio-button value="90d">近90天</el-radio-button>
        </el-radio-group>
        <el-button
          type="primary"
          size="small"
          :loading="loading"
          @click="refreshData"
          class="refresh-btn"
        >
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="dashboard-content">
      <!-- 左侧面板：板块导航 -->
      <aside class="panel sectors-panel" aria-label="板块导航">
        <div class="panel-header">
          <span class="panel-title">板块导航</span>
          <span class="panel-count">已选 {{ activeSectors.length }}/{{ allLeafSectorCodes.length }} 板块</span>
        </div>
        <div class="sector-list">
          <div
            v-for="category in sectorList"
            :key="category.code"
            class="sector-category"
          >
            <div
              class="category-header"
              @click="toggleCategory(category.code)"
            >
              <el-icon :size="12" class="category-arrow" :class="{ expanded: expandedCategories[category.code] }">
                <ArrowRight />
              </el-icon>
              <span class="category-name">{{ category.name }}</span>
              <span class="category-count">{{ category.children.filter(c => activeSectors.includes(c.code)).length }}/{{ category.children.length }}</span>
            </div>
            <div v-show="expandedCategories[category.code]" class="category-children">
              <div
                v-for="sector in category.children"
                :key="sector.code"
                :class="['sector-item', { active: activeSectors.includes(sector.code) }]"
                @click="toggleSector(sector.code)"
                :title="activeSectors.length === 1 && activeSectors.includes(sector.code) ? '至少保留一个板块' : ''"
              >
                <span class="sector-color" :style="{ backgroundColor: sector.color }"></span>
                <span class="sector-name">{{ sector.name }}</span>
                <span
                  class="sector-value"
                  :class="getIndexColorClass(getSectorIndex(sector.code))"
                >
                  {{ formatIndex(getSectorIndex(sector.code)) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </aside>

      <!-- 中间面板：图表区 -->
      <section class="panel charts-panel" aria-label="数据图表">
        <!-- 骨架屏 -->
        <template v-if="loading && !overviewData">
          <div class="loading-overlay">
            <div class="skeleton-grid">
              <div class="skeleton-card metric-skeleton"></div>
              <div class="skeleton-card metric-skeleton"></div>
              <div class="skeleton-card chart-skeleton main-chart"></div>
              <div class="skeleton-card chart-skeleton"></div>
              <div class="skeleton-card chart-skeleton"></div>
            </div>
          </div>
        </template>

        <!-- 错误状态 -->
        <template v-else-if="error">
          <div class="error-state">
            <div class="error-icon">
              <el-icon :size="56"><WarningFilled /></el-icon>
            </div>
            <h3 class="error-title">数据加载失败</h3>
            <p class="error-text">{{ error }}</p>
            <el-button type="primary" @click="refreshData">重新加载</el-button>
          </div>
        </template>

        <!-- 图表内容 -->
        <template v-else>
          <!-- 顶部指标卡片 -->
          <div class="metrics-row">
            <div class="metric-card overview-card">
              <div class="metric-header">
                <span class="metric-label">综合情绪指数</span>
                <span class="metric-badge" :class="getIndexColorClass(overviewData?.avg_index || 0)">
                  {{ getIndexLabel(overviewData?.avg_index || 0) }}
                </span>
              </div>
              <div class="metric-value" :class="getIndexColorClass(overviewData?.avg_index || 0)">
                {{ formatIndex(overviewData?.avg_index) }}
              </div>
              <div class="metric-sub">
                覆盖 <strong>{{ overviewData?.sector_count || 0 }}</strong>/{{ allLeafSectorCodes.length }} 个子板块
              </div>
            </div>
            <div class="metric-card gauge-card">
              <GaugeChart
                :value="overviewData?.avg_index || 0"
                name="市场热度"
                :max="100"
                height="200px"
              />
            </div>
          </div>

          <!-- 折线图 -->
          <div class="chart-card main-chart">
            <div class="chart-header">
              <div class="chart-title-wrap">
                <span class="chart-title">情绪走势</span>
                <span class="chart-subtitle">{{ chartSubtitle }}</span>
              </div>
              <span v-if="lineChartError" class="chart-error-tag">
                <el-tag type="danger" size="small" effect="plain">加载失败</el-tag>
                <el-button type="primary" size="small" link @click="refreshLineChart">重试</el-button>
              </span>
            </div>
            <div class="chart-body">
              <LineChart
                v-if="lineChartSeries && lineChartSeries.length > 0"
                :xAxisData="lineChartData.x_axis"
                :seriesData="lineChartSeries"
                :legendData="lineChartLegend"
                :nameMap="SECTOR_NAMES"
                :showArea="true"
                height="320px"
              />
              <div v-else-if="lineChartError" class="chart-empty">
                <el-empty description="数据加载失败" :image-size="80" />
              </div>
              <div v-else class="chart-empty">
                <el-empty description="暂无数据" :image-size="80" />
              </div>
            </div>
          </div>

          <!-- 底部两个图表 -->
          <div class="bottom-charts">
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">板块排行</span>
              </div>
              <div class="chart-body">
                <BarChart
                  v-if="sectorRankingData && sectorRankingData.length > 0"
                  :categories="sectorRankingData.map(d => d.name)"
                  :seriesData="[{ name: '情绪指数', data: sectorRankingData.map(d => d.value), itemStyle: { borderRadius: [6, 6, 0, 0] } }]"
                  :horizontal="true"
                  height="240px"
                />
                <div v-else class="chart-empty">
                  <el-empty description="暂无数据" :image-size="64" />
                </div>
              </div>
            </div>
            <div class="chart-card">
              <div class="chart-header">
                <span class="chart-title">板块占比</span>
              </div>
              <div class="chart-body">
                <PieChart
                  v-if="pieChartData && pieChartData.length > 0"
                  :data="pieChartData"
                  height="240px"
                  :radius="['40%', '70%']"
                />
                <div v-else class="chart-empty">
                  <el-empty description="暂无数据" :image-size="64" />
                </div>
              </div>
            </div>
          </div>
        </template>
      </section>

      <!-- 右侧面板：板块详情 -->
      <aside class="panel details-panel" aria-label="板块详情">
        <div class="panel-header">
          <span class="panel-title">板块详情</span>
        </div>
        <div class="sector-detail-list">
          <div
            v-for="sector in activeSectorDetails"
            :key="sector.code"
            class="detail-card"
            :style="{ '--sector-color': sector.color }"
          >
            <div class="detail-header">
              <div class="detail-name-wrap">
                <span class="detail-dot" :style="{ backgroundColor: sector.color }"></span>
                <span class="detail-name">{{ sector.name }}</span>
              </div>
              <span class="detail-index" :class="getIndexColorClass(sector.index)">
                {{ formatIndex(sector.index) }}
              </span>
            </div>
            <div class="detail-meta">
              <div class="meta-item">
                <span class="meta-label">帖子数</span>
                <span class="meta-value">{{ formatNumber(sector.post_count) }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">正面率</span>
                <span class="meta-value positive">{{ sector.positive_ratio ?? '--' }}%</span>
              </div>
              <div class="meta-item">
                <span class="meta-label">趋势</span>
                <span :class="['meta-value', 'trend-value', getTrendClass(sector.trend)]">
                  {{ sector.trend || '平稳' }}
                </span>
              </div>
            </div>
          </div>
          <el-empty v-if="activeSectorDetails.length === 0" description="请选择板块" :image-size="64" />
        </div>
      </aside>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { ElMessage } from 'element-plus'
import { Refresh, WarningFilled, ArrowRight } from '@element-plus/icons-vue'
import LineChart from '@/components/Chart/LineChart.vue'
import BarChart from '@/components/Chart/BarChart.vue'
import PieChart from '@/components/Chart/PieChart.vue'
import GaugeChart from '@/components/Chart/GaugeChart.vue'
import { SECTOR_NAMES, SECTOR_COLORS, SECTOR_CATEGORIES } from '@/api/index'

const store = useDashboardStore()
const loading = ref(false)
const error = ref('')
const timeRange = ref('7d')
// 所有叶子板块代码
const allLeafSectorCodes = computed(() => {
  const codes = []
  SECTOR_CATEGORIES.forEach(cat => codes.push(...cat.children))
  return codes
})

const activeSectors = ref([...allLeafSectorCodes.value])
const lineChartError = ref(false)

// 父板块展开状态（默认全部展开）
const expandedCategories = ref(
  Object.fromEntries(SECTOR_CATEGORIES.map(cat => [cat.code, true]))
)

// 板块列表（按父板块分组）
const sectorList = computed(() => {
  return SECTOR_CATEGORIES.map(cat => ({
    code: cat.code,
    name: cat.name,
    isCategory: true,
    children: cat.children.map(code => ({
      code,
      name: SECTOR_NAMES[code] || code,
      color: SECTOR_COLORS[code] || '#0ea5e9',
      category: cat.code
    }))
  }))
})

// 从 store 获取数据
const overviewData = computed(() => store.overviewData)
const lineChartData = computed(() => store.lineChartData)

// 折线图系列名称映射为中文
const lineChartSeries = computed(() => {
  const data = lineChartData.value?.series_data
  if (!data) return []
  return data.map(item => ({
    ...item,
    name: SECTOR_NAMES[item.name] || item.name
  }))
})

const lineChartLegend = computed(() => {
  return lineChartSeries.value.map(item => item.name)
})

const activeSectorNames = computed(() => {
  return activeSectors.value.map(code => SECTOR_NAMES[code] || code)
})

// 折线图副标题：全选时显示"全部板块"，超过4个时显示前3个+"等N个板块"
const chartSubtitle = computed(() => {
  const count = activeSectorNames.value.length
  const total = allLeafSectorCodes.value.length
  if (count === 0) return '全部板块'
  if (count === total) return `全部板块（${count}）`
  if (count <= 4) return activeSectorNames.value.join(' / ')
  return `${activeSectorNames.value.slice(0, 3).join(' / ')} 等${count}个板块`
})

// 板块排行数据
const sectorRankingData = computed(() => {
  const sectors = overviewData.value?.sectors
  if (!sectors) return []
  return Object.entries(sectors)
    .filter(([code]) => activeSectors.value.includes(code))
    .map(([code, data]) => ({
      code,
      name: SECTOR_NAMES[code] || code,
      value: data?.index ?? 0,
      color: SECTOR_COLORS[code] || '#0ea5e9'
    }))
    .sort((a, b) => b.value - a.value)
})

// 饼图数据
const pieChartData = computed(() => {
  return sectorRankingData.value.map(item => ({
    name: item.name,
    value: item.value,
    itemStyle: { color: item.color }
  }))
})

// 活跃板块详情
const activeSectorDetails = computed(() => {
  const sectors = overviewData.value?.sectors
  if (!sectors) return []
  return activeSectors.value
    .map(code => {
      const data = sectors[code]
      if (!data) return null
      return {
        code,
        name: SECTOR_NAMES[code] || code,
        index: data.index ?? 0,
        post_count: data.post_count ?? 0,
        positive_ratio: data.positive_ratio ?? 0,
        trend: data.trend ?? '平稳',
        color: SECTOR_COLORS[code] || '#0ea5e9'
      }
    })
    .filter(Boolean)
})

// 获取板块指数
function getSectorIndex(code) {
  const sector = overviewData.value?.sectors?.[code]
  return sector?.index ?? 0
}

// 指数颜色
function getIndexColorClass(value) {
  if (value >= 60) return 'index-hot'
  if (value >= 40) return 'index-warm'
  if (value >= 20) return 'index-cool'
  return 'index-cold'
}

function getIndexLabel(value) {
  if (value >= 60) return '过热'
  if (value >= 40) return '活跃'
  if (value >= 20) return '温和'
  return '冷清'
}

// 趋势颜色
function getTrendClass(trend) {
  if (trend === '上涨') return 'trend-up'
  if (trend === '下跌') return 'trend-down'
  return 'trend-flat'
}

// 时间格式化
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

// 数字格式化
function formatNumber(num) {
  if (num === null || num === undefined) return '--'
  return num.toLocaleString('zh-CN')
}

// 情绪指数统一格式化为两位小数
function formatIndex(num) {
  if (num === null || num === undefined || num === '') return '--'
  const value = Number(num)
  if (Number.isNaN(value)) return '--'
  return value.toFixed(2)
}

// 切换板块
function toggleSector(code) {
  const idx = activeSectors.value.indexOf(code)
  if (idx >= 0) {
    // 至少保留一个板块
    if (activeSectors.value.length <= 1) {
      ElMessage.warning('至少保留一个板块')
      return
    }
    activeSectors.value.splice(idx, 1)
  } else {
    activeSectors.value.push(code)
    if (activeSectors.value.length > 6) {
      activeSectors.value.shift()
    }
  }
  refreshLineChart()
}

// 时间范围切换
function handleTimeRangeChange() {
  refreshLineChart()
}

let refreshLineChartTimer = null

// 刷新折线图（防抖 150ms，避免快速切换板块时连续请求与图表重绘）
async function refreshLineChart() {
  if (refreshLineChartTimer) clearTimeout(refreshLineChartTimer)
  refreshLineChartTimer = setTimeout(async () => {
    lineChartError.value = false
    try {
      const days = timeRange.value === '7d' ? 7 : timeRange.value === '30d' ? 30 : 90
      await store.fetchLineChart(activeSectors.value, days)
    } catch (e) {
      lineChartError.value = true
      console.error('折线图数据加载失败:', e)
    }
  }, 150)
}

// 刷新所有数据
async function refreshData() {
  loading.value = true
  error.value = ''
  lineChartError.value = false
  try {
    const days = timeRange.value === '7d' ? 7 : timeRange.value === '30d' ? 30 : 90
    await store.fetchAll(activeSectors.value, days)
    await refreshLineChart()
  } catch (e) {
    error.value = e?.message || '数据加载失败，请检查后端服务是否运行'
    console.error('数据加载失败:', e)
  } finally {
    loading.value = false
  }
}

// 监听 store 错误
watch(() => store.error, (newError) => {
  if (newError) {
    error.value = newError
  }
})

onMounted(() => {
  refreshData()
})

onUnmounted(() => {
  if (refreshLineChartTimer) {
    clearTimeout(refreshLineChartTimer)
    refreshLineChartTimer = null
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.dashboard-page {
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: $spacing-5 $spacing-6 $spacing-6;
  gap: $spacing-5;

  @media (max-width: $breakpoint-md) {
    padding: $spacing-4 $spacing-4 calc($spacing-4 + 60px);
    gap: $spacing-4;
  }
}

// 工具栏
.dashboard-toolbar {
  @include flex-between;
  flex-shrink: 0;
  gap: $spacing-3;

  .toolbar-left {
    display: flex;
    align-items: baseline;
    gap: $spacing-4;
  }

  .page-title {
    font-size: $font-size-2xl;
    font-weight: $font-weight-bold;
    color: $color-text-primary;
    letter-spacing: -0.02em;
  }

  .update-time {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    font-size: $font-size-sm;
    color: $color-text-tertiary;

    .time-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background-color: $color-success;
      animation: pulse 2s ease-in-out infinite;
    }
  }

  .toolbar-right {
    display: flex;
    align-items: center;
    gap: $spacing-3;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  @media (max-width: $breakpoint-md) {
    flex-direction: column;
    align-items: flex-start;

    .toolbar-left {
      width: 100%;
    }

    .toolbar-right {
      width: 100%;
      justify-content: space-between;
    }

    .update-time {
      display: none;
    }
  }
}

// 主内容网格
.dashboard-content {
  flex: 1;
  display: grid;
  grid-template-columns: 220px 1fr 280px;
  gap: $spacing-5;
  min-height: 0;

  @media (max-width: $breakpoint-xl) {
    grid-template-columns: 200px 1fr 260px;
    gap: $spacing-4;
  }

  @media (max-width: $breakpoint-lg) {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr auto;
    overflow-y: auto;
    // 避免滚动链导致整页抖动，开启硬件滚动
    overscroll-behavior: contain;
    -webkit-overflow-scrolling: touch;
  }

  @media (max-width: $breakpoint-md) {
    gap: $spacing-3;
  }
}

.panel {
  @include card-style;
  padding: $spacing-4;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.panel-header {
  @include flex-between;
  margin-bottom: $spacing-4;
  flex-shrink: 0;

  .panel-title {
    font-size: $font-size-sm;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
    letter-spacing: 0.02em;
  }

  .panel-count {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
    font-weight: $font-weight-medium;
  }
}

// 左侧面板
.sectors-panel {
  @media (max-width: $breakpoint-lg) {
    max-height: 160px;
  }

  @media (max-width: $breakpoint-md) {
    max-height: none;
    padding: $spacing-3;
  }
}

.sector-list {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  @include custom-scrollbar(4px);

  @media (max-width: $breakpoint-lg) {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-2;
    overflow-x: auto;
    overflow-y: hidden;
  }
}

.sector-category {
  margin-bottom: $spacing-2;

  &:last-child {
    margin-bottom: 0;
  }
}

.category-header {
  display: flex;
  align-items: center;
  gap: $spacing-2;
  padding: $spacing-2 $spacing-3;
  border-radius: $radius-md;
  cursor: pointer;
  color: $color-text-secondary;
  font-size: $font-size-sm;
  font-weight: $font-weight-semibold;
  user-select: none;

  &:hover {
    background: $color-bg-hover;
  }

  .category-arrow {
    transition: transform $transition-fast;
    transform: rotate(0deg);

    &.expanded {
      transform: rotate(90deg);
    }
  }

  .category-name {
    flex: 1;
  }

  .category-count {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
    font-weight: $font-weight-medium;
  }
}

.category-children {
  // v-show 切换无过渡，避免 height 动画带来的布局抖动
  contain: layout;
}

.sector-item {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  padding: $spacing-2 $spacing-3;
  margin-bottom: $spacing-2;
  border-radius: $radius-md;
  cursor: pointer;
  // 仅对 transform 做过渡；背景与边框变化即时生效，避免重绘
  transition: transform $transition-fast;
  border-left: 3px solid transparent;
  backface-visibility: hidden;
  // 限制单元素绘制范围，提升长列表滚动性能
  contain: layout paint;

  &:hover {
    background: $color-bg-hover;
    transform: translateX(2px);
    will-change: transform;
  }

  &.active {
    background: $color-primary-100;
    border-left-color: $color-primary;
  }

  .sector-color {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .sector-name {
    flex: 1;
    color: $color-text-secondary;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    min-width: 0;
    @include ellipsis;
  }

  .sector-value {
    @include numeric-font;
    font-size: $font-size-xs;
    font-weight: $font-weight-bold;
    flex-shrink: 0;
  }

  @media (max-width: $breakpoint-lg) {
    margin-bottom: 0;
    white-space: nowrap;
    flex: 0 0 auto;
  }

  @media (max-width: $breakpoint-md) {
    padding: $spacing-1 $spacing-2;
  }
}

// 中间图表面板
.charts-panel {
  gap: $spacing-4;
  padding: $spacing-4;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  @include custom-scrollbar(6px);

  @media (max-width: $breakpoint-md) {
    padding: $spacing-3;
    gap: $spacing-3;
    overflow-y: visible;
  }
}

.loading-overlay {
  display: flex;
  flex-direction: column;
  gap: $spacing-4;
}

.skeleton-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-4;

  .metric-skeleton {
    height: 160px;
  }

  .main-chart {
    grid-column: 1 / -1;
    height: 320px;
  }

  .chart-skeleton {
    height: 240px;
  }

  @media (max-width: $breakpoint-md) {
    grid-template-columns: 1fr;

    .main-chart,
    .chart-skeleton,
    .metric-skeleton {
      grid-column: 1 / -1;
      height: 220px;
    }

    .metric-skeleton {
      height: 140px;
    }
  }
}

.error-state {
  @include flex-center;
  flex-direction: column;
  gap: $spacing-4;
  padding: $spacing-12;
  color: $color-danger;
  text-align: center;

  .error-icon {
    padding: $spacing-5;
    border-radius: 50%;
    background: $color-danger-100;
  }

  .error-title {
    color: $color-text-primary;
    font-size: $font-size-xl;
    font-weight: $font-weight-semibold;
  }

  .error-text {
    color: $color-text-secondary;
    font-size: $font-size-base;
    max-width: 480px;
  }
}

.metrics-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-4;
  flex-shrink: 0;

  @media (max-width: $breakpoint-md) {
    grid-template-columns: 1fr;
  }
}

.metric-card {
  @include card-style;
  padding: $spacing-5;
  display: flex;
  flex-direction: column;
  justify-content: center;

  &.overview-card {
    .metric-header {
      @include flex-between;
      margin-bottom: $spacing-4;
    }

    .metric-label {
      font-size: $font-size-sm;
      color: $color-text-secondary;
      font-weight: $font-weight-medium;
    }

    .metric-badge {
      font-size: $font-size-xs;
      font-weight: $font-weight-bold;
      padding: 2px 8px;
      border-radius: $radius-full;
      background: currentColor;
      color: $color-text-inverse;

      &.index-hot { background: $color-danger; }
      &.index-warm { background: $color-warning; }
      &.index-cool { background: $color-primary; }
      &.index-cold { background: $color-text-tertiary; }
    }

    .metric-value {
      @include numeric-font;
      font-size: $font-size-5xl;
      font-weight: $font-weight-bold;
      line-height: 1;
      margin-bottom: $spacing-3;
    }

    .metric-sub {
      font-size: $font-size-sm;
      color: $color-text-tertiary;

      strong {
        color: $color-text-primary;
        font-weight: $font-weight-semibold;
      }
    }
  }

  &.gauge-card {
    padding: $spacing-3;
    min-width: 0;
  }

  @media (max-width: $breakpoint-md) {
    &.overview-card .metric-value {
      font-size: $font-size-4xl;
    }
  }
}

.index-hot { color: $color-danger; }
.index-warm { color: $color-warning; }
.index-cool { color: $color-primary; }
.index-cold { color: $color-text-tertiary; }

.chart-card {
  @include card-style;
  padding: $spacing-4;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;

  .chart-header {
    @include flex-between;
    margin-bottom: $spacing-3;
    flex-shrink: 0;
    gap: $spacing-3;
  }

  .chart-title-wrap {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .chart-title {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .chart-subtitle {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
    // 超长副标题截断，避免换行挤压图表
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 400px;
  }

  .chart-error-tag {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .chart-body {
    flex: 1;
    min-height: 0;
  }

  .chart-empty {
    @include flex-center;
    flex: 1;
    min-height: 150px;
  }
}

.bottom-charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: $spacing-4;
  flex-shrink: 0;

  @media (max-width: $breakpoint-md) {
    grid-template-columns: 1fr;
  }
}

// 右侧面板
.details-panel {
  @media (max-width: $breakpoint-lg) {
    max-height: 360px;
  }
}

.sector-detail-list {
  flex: 1;
  overflow-y: auto;
  overscroll-behavior: contain;
  -webkit-overflow-scrolling: touch;
  @include custom-scrollbar(4px);
}

.detail-card {
  position: relative;
  background: $color-bg-input;
  border-radius: $radius-md;
  padding: $spacing-3;
  margin-bottom: $spacing-3;
  overflow: hidden;
  // 仅过渡 transform，颜色变化即时生效，避免重绘
  transition: transform $transition-fast;
  backface-visibility: hidden;
  // 限制单卡片绘制范围，提升长列表滚动性能
  contain: layout paint;

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 4px;
    height: 100%;
    background: var(--sector-color);
  }

  &:hover {
    background: $color-bg-hover;
    transform: translateX(2px);
    will-change: transform;
  }
}

.detail-header {
  @include flex-between;
  margin-bottom: $spacing-3;

  .detail-name-wrap {
    display: flex;
    align-items: center;
    gap: $spacing-2;
  }

  .detail-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .detail-name {
    font-size: $font-size-base;
    font-weight: $font-weight-semibold;
    color: $color-text-primary;
  }

  .detail-index {
    @include numeric-font;
    font-size: $font-size-xl;
    font-weight: $font-weight-bold;
  }
}

.detail-meta {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: $spacing-2;

  .meta-item {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .meta-label {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
  }

  .meta-value {
    font-size: $font-size-sm;
    color: $color-text-secondary;
    @include numeric-font;
    font-weight: $font-weight-medium;

    &.positive {
      color: $color-success;
    }
  }

  .trend-value {
    font-weight: $font-weight-semibold;
  }
}

.trend-up { color: $color-danger; }
.trend-down { color: $color-success; }
.trend-flat { color: $color-text-tertiary; }
</style>
