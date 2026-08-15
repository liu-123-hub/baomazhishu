<template>
  <div class="ios-ratio-chart">
    
    <div class="ratio-toolbar">
      <div class="toolbar-left">
        <span class="ratio-label">创业板指 / 中证红利</span>
      </div>
      <IOSSegmentControl
        v-model="currentUnit"
        :options="unitOptions"
        aria-label="时间单位切换"
        @update:modelValue="handleUnitChange"
      />
    </div>

    
    <div class="ratio-chart-wrapper">
      <div v-if="loading" class="chart-loading">
        <div class="ios-spinner" aria-hidden="true"></div>
        <span class="loading-text">加载比值数据中...</span>
      </div>
      <div v-else-if="error" class="chart-placeholder">
        <span class="placeholder-icon" aria-hidden="true">⚠️</span>
        <span class="placeholder-text">{{ error }}</span>
        <button class="ios-button ios-button-secondary" @click="fetchData">点击重试</button>
      </div>
      <div v-else-if="!hasData" class="chart-placeholder">
        <span class="placeholder-icon" aria-hidden="true">📊</span>
        <span class="placeholder-text">暂无比值数据</span>
      </div>
      <div v-show="!loading && !error && hasData" ref="chartRef" class="chart-container" :style="{ height: height }"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '@/stores/theme'
import { dashboardApi } from '@/core/api'
import IOSSegmentControl from '@/components/ios/IOSSegmentControl.vue'


echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  DataZoomComponent,
  MarkLineComponent,
  CanvasRenderer
])

const props = defineProps({
  height: {
    type: String,
    default: '360px'
  }
})

const themeStore = useThemeStore()
const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null
let rafId = null


const currentUnit = ref('month')
const unitOptions = [
  { label: '年', value: 'year' },
  { label: '季度', value: 'quarter' },
  { label: '月', value: 'month' }
]
const loading = ref(false)
const error = ref('')
const chartData = ref(null)


let isPageVisible = true
let pendingUpdate = false

function handleVisibilityChange() {
  const wasVisible = isPageVisible
  isPageVisible = document.visibilityState === 'visible'
  if (isPageVisible && !wasVisible && pendingUpdate) {
    pendingUpdate = false
    nextTick(() => updateChart())
  }
}

const hasData = computed(() => {
  return chartData.value && chartData.value.ratios && chartData.value.ratios.length > 0
})


async function fetchData() {
  loading.value = true
  error.value = ''
  try {
    const res = await dashboardApi.getIndexRatio(currentUnit.value)
    if (res?.code === 200 && res?.data) {
      chartData.value = res.data
    } else {
      chartData.value = null
      error.value = res?.message || '获取比值数据失败'
    }
  } catch (e) {
    chartData.value = null
    error.value = e?.userMessage || e?.message || '网络请求失败'
  } finally {
    loading.value = false
  }
}

function handleUnitChange() {
  fetchData()
}


const chartOption = computed(() => {
  const isDark = themeStore.isDark
  const textColor = isDark ? 'rgba(235, 235, 245, 0.85)' : 'rgba(60, 60, 67, 0.85)'
  const subTextColor = isDark ? 'rgba(235, 235, 245, 0.55)' : 'rgba(60, 60, 67, 0.55)'
  const gridColor = isDark ? 'rgba(84, 84, 88, 0.4)' : 'rgba(60, 60, 67, 0.12)'
  const tooltipBg = isDark ? 'rgba(44, 44, 46, 0.98)' : 'rgba(255, 255, 255, 0.98)'
  const tooltipBorder = isDark ? 'rgba(84, 84, 88, 0.6)' : 'rgba(60, 60, 67, 0.1)'

  
  const areaMainColor = '#007AFF'
  const areaGradientTop = 'rgba(0, 122, 255, 0.35)'
  const areaGradientBottom = 'rgba(0, 122, 255, 0.02)'

  if (!hasData.value) return {}

  const xAxis = chartData.value.x_axis || []
  const ratios = chartData.value.ratios || []
  const chinextValues = chartData.value.chinext_values || []
  const dividendValues = chartData.value.dividend_values || []
  const nameA = chartData.value.index_names?.a || '创业板指'
  const nameB = chartData.value.index_names?.b || '中证红利'

  const dataCount = xAxis.length
  
  const isDense = dataCount > 14
  const rotate = isDense ? 35 : 0
  const bottomMargin = isDense ? 80 : 64
  const labelInterval = dataCount <= 7 ? 0 : dataCount <= 14 ? 1 : Math.floor(dataCount / 7)

  return {
    animation: true,
    animationDuration: 600,
    animationEasing: 'cubicOut',
    tooltip: {
      trigger: 'axis',
      triggerOn: 'mousemove|click',
      backgroundColor: tooltipBg,
      borderColor: tooltipBorder,
      borderWidth: 1,
      padding: [12, 16],
      borderRadius: 14,
      confine: true,
      appendToBody: true,
      extraCssText: 'box-shadow: 0 4px 20px rgba(0,0,0,0.15), 0 2px 8px rgba(0,0,0,0.1); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px); z-index: 99999;',
      textStyle: {
        color: textColor,
        fontSize: 13,
        fontWeight: 500,
        fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display", sans-serif'
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: gridColor,
          width: 1,
          type: 'dashed'
        },
        label: { show: false },
        z: 0
      },
      
      formatter: function (params) {
        if (!params || !params.length) return ''
        const idx = params[0].dataIndex
        const label = xAxis[idx] || ''
        const ratio = ratios[idx]
        const valA = chinextValues[idx]
        const valB = dividendValues[idx]

        let html = `<div style="font-weight:600;margin-bottom:8px;font-size:13px;color:${textColor}">${label}</div>`

        
        html += `<div style="display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${areaMainColor}"></span>
          <span style="color:${subTextColor};flex:1">比值</span>
          <span style="color:${areaMainColor};font-weight:700;font-size:15px">${ratio != null ? ratio.toFixed(4) : '--'}</span>
        </div>`

        
        html += `<div style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:12px">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#FF9500"></span>
          <span style="color:${subTextColor};flex:1">${nameA}</span>
          <span style="color:${textColor};font-weight:600">${valA != null ? valA.toFixed(2) : '--'}</span>
        </div>`

        
        html += `<div style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:12px">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#34C759"></span>
          <span style="color:${subTextColor};flex:1">${nameB}</span>
          <span style="color:${textColor};font-weight:600">${valB != null ? valB.toFixed(2) : '--'}</span>
        </div>`

        return html
      }
    },
    grid: {
      top: 24,
      left: 52,
      right: 20,
      bottom: bottomMargin,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxis,
      boundaryGap: false,
      axisLine: {
        show: true,
        lineStyle: { color: gridColor, width: 1 }
      },
      axisTick: { show: false },
      axisLabel: {
        color: subTextColor,
        fontSize: 11,
        margin: 12,
        showMaxLabel: true,
        showMinLabel: true,
        hideOverlap: true,
        interval: labelInterval,
        align: isDense ? 'right' : 'center',
        rotate: rotate
      }
    },
    yAxis: {
      type: 'value',
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: {
        color: subTextColor,
        fontSize: 11,
        margin: 10,
        showMaxLabel: true,
        showMinLabel: true,
        formatter: (value) => value.toFixed(2)
      },
      splitLine: {
        lineStyle: {
          color: gridColor,
          width: 1,
          type: 'solid'
        }
      },
      
      min: (value) => {
        const range = value.max - value.min
        return Math.floor((value.min - range * 0.1) * 100) / 100
      },
      max: (value) => {
        const range = value.max - value.min
        return Math.ceil((value.max + range * 0.1) * 100) / 100
      }
    },
    
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomLock: false,
        throttle: 50
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 22,
        bottom: 14,
        borderColor: 'transparent',
        backgroundColor: isDark ? 'rgba(120, 120, 128, 0.16)' : 'rgba(120, 120, 128, 0.08)',
        fillerColor: 'rgba(0, 122, 255, 0.12)',
        handleStyle: {
          color: '#fff',
          borderColor: areaMainColor,
          borderWidth: 1.5,
          shadowBlur: 4,
          shadowColor: 'rgba(0,0,0,0.15)'
        },
        moveHandleStyle: {
          color: areaMainColor,
          opacity: 0.6
        },
        textStyle: {
          color: subTextColor,
          fontSize: 10
        },
        dataBackground: {
          lineStyle: { color: isDark ? 'rgba(120, 120, 128, 0.3)' : 'rgba(120, 120, 128, 0.2)' },
          areaStyle: {
            color: isDark ? 'rgba(120, 120, 128, 0.1)' : 'rgba(120, 120, 128, 0.06)'
          }
        },
        selectedDataBackground: {
          lineStyle: { color: areaMainColor, opacity: 0.4 },
          areaStyle: { color: areaMainColor, opacity: 0.1 }
        }
      }
    ],
    series: [
      {
        name: '创业板指/中证红利',
        type: 'line',
        data: ratios,
        smooth: true,
        connectNulls: true,
        showSymbol: false,
        symbol: 'circle',
        symbolSize: 6,
        z: 3,
        lineStyle: {
          width: 2.5,
          color: areaMainColor
        },
        
        areaStyle: {
          opacity: 1,
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: areaGradientTop },
            { offset: 1, color: areaGradientBottom }
          ])
        },
        itemStyle: {
          color: areaMainColor,
          borderWidth: 2,
          borderColor: '#fff'
        },
        emphasis: {
          scale: true,
          focus: 'series',
          showSymbol: true,
          z: 10,
          lineStyle: { width: 3.5 },
          itemStyle: {
            borderWidth: 2,
            borderColor: '#fff',
            shadowBlur: 6,
            shadowColor: 'rgba(0,0,0,0.15)'
          }
        },
        
        markLine: {
          silent: true,
          symbol: 'none',
          lineStyle: {
            color: isDark ? 'rgba(255, 149, 0, 0.4)' : 'rgba(255, 149, 0, 0.3)',
            type: 'dashed',
            width: 1
          },
          label: {
            show: true,
            position: 'insideEndTop',
            formatter: '比值 1.0',
            color: subTextColor,
            fontSize: 10
          },
          data: [{ yAxis: 1.0 }]
        }
      }
    ]
  }
})


function initChart() {
  if (!chartRef.value) return

  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }

  if (chartInstance) {
    if (!chartInstance.isDisposed()) {
      chartInstance.dispose()
    }
    chartInstance = null
  }

  chartInstance = echarts.init(chartRef.value, null, {
    renderer: 'canvas'
  })
  chartInstance.setOption(chartOption.value, { notMerge: true })
}

function updateChart() {
  if (!chartInstance || chartInstance.isDisposed()) return

  if (!isPageVisible) {
    pendingUpdate = true
    return
  }

  if (rafId) cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(() => {
    if (!chartInstance || chartInstance.isDisposed()) return
    chartInstance.setOption(chartOption.value, { notMerge: true })
  })
}

function scheduleResize() {
  if (rafId) cancelAnimationFrame(rafId)
  rafId = requestAnimationFrame(() => {
    chartInstance?.resize()
  })
}


watch(
  () => chartData.value,
  () => {
    nextTick(() => {
      if (hasData.value && !chartInstance) {
        initChart()
      } else if (hasData.value) {
        updateChart()
      }
    })
  },
  { deep: true }
)


watch(
  () => themeStore.isDark,
  () => {
    nextTick(() => {
      if (hasData.value) {
        initChart()
      }
    })
  }
)

onMounted(() => {
  fetchData()
  document.addEventListener('visibilitychange', handleVisibilityChange)
  isPageVisible = document.visibilityState === 'visible'

  if (window.ResizeObserver && chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      scheduleResize()
    })
    resizeObserver.observe(chartRef.value)
  } else {
    window.addEventListener('resize', scheduleResize, { passive: true })
  }
})

onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
  if (resizeObserver) {
    resizeObserver.disconnect()
  } else {
    window.removeEventListener('resize', scheduleResize)
  }
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})

defineExpose({
  resize: scheduleResize,
  refresh: fetchData,
  getInstance: () => chartInstance
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-ratio-chart {
  width: 100%;
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  overflow: visible;
  padding: 8px;
  box-sizing: border-box;
}

.ratio-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ios-spacing-sm) var(--ios-spacing-md) var(--ios-spacing-md);
  gap: var(--ios-spacing-md);
  flex-wrap: wrap;

  @include mobile {
    flex-direction: column;
    align-items: stretch;
    gap: var(--ios-spacing-sm);
  }
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
}

.ratio-label {
  font-size: var(--ios-text-sm);
  font-weight: 600;
  color: var(--ios-label-primary);
  letter-spacing: -0.01em;
}

.ratio-chart-wrapper {
  width: 100%;
  position: relative;
}

.chart-container {
  width: 100%;
  min-height: 300px;

  @include mobile {
    min-height: 260px;
  }
}

.chart-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 360px;
  gap: var(--ios-spacing-md);

  @include mobile {
    height: 260px;
  }
}

.ios-spinner {
  width: 28px;
  height: 28px;
  border: 2.5px solid var(--ios-fill-tertiary);
  border-top-color: var(--ios-blue);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: var(--ios-text-sm);
  color: var(--ios-label-secondary);
}

.chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 360px;
  gap: var(--ios-spacing-md);

  @include mobile {
    height: 260px;
  }
}

.placeholder-icon {
  font-size: 40px;
  opacity: 0.5;
}

.placeholder-text {
  color: var(--ios-label-tertiary);
  font-size: var(--ios-text-sm);
}

.ios-button {
  @include ios-button;
}

.ios-button-secondary {
  @include ios-button-secondary;
}

@media (prefers-reduced-motion: reduce) {
  .ios-spinner {
    animation: none;
  }
}
</style>
