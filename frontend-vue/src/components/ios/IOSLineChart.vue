<template>
  <div class="ios-line-chart">
    <div ref="chartRef" class="chart-container" :style="{ height: height }"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useThemeStore } from '@/stores/theme'

echarts.use([
  LineChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  CanvasRenderer
])

const props = defineProps({
  data: {
    type: Object,
    default: () => ({ x_axis: [], legend: [], series_data: [] })
  },
  height: {
    type: String,
    default: '340px'
  }
})

const themeStore = useThemeStore()
const chartRef = ref(null)
let chartInstance = null
let resizeObserver = null
let rafId = null

const colors = [
  '#007AFF',
  '#34C759',
  '#FF3B30',
  '#FF9500',
  '#AF52DE',
  '#5AC8FA',
  '#FF2D55',
  '#5856D6',
  '#00C7BE',
  '#FFD60A',
  '#8E8E93',
  '#30D158',
  '#FF6482',
  '#BF5AF2',
  '#64D2FF',
  '#FFA800',
  '#0A84FF',
  '#32D74B',
  '#FF453A',
  '#FF9F0A',
  '#7B61FF',
  '#5E5CE6',
  '#007BFF',
  '#28CD41',
  '#D70015'
]

const chartOption = computed(() => {
  const isDark = themeStore.isDark
  const textColor = isDark ? 'rgba(235, 235, 245, 0.8)' : 'rgba(60, 60, 67, 0.8)'
  const subTextColor = isDark ? 'rgba(235, 235, 245, 0.5)' : 'rgba(60, 60, 67, 0.5)'
  const gridColor = isDark ? 'rgba(84, 84, 88, 0.4)' : 'rgba(60, 60, 67, 0.12)'
  const tooltipBg = isDark ? 'rgba(44, 44, 46, 0.98)' : 'rgba(255, 255, 255, 0.98)'
  const tooltipBorder = isDark ? 'rgba(84, 84, 88, 0.6)' : 'rgba(60, 60, 67, 0.1)'

  const xAxis = props.data?.x_axis || []
  const legend = props.data?.legend || []
  const seriesData = props.data?.series_data || []

  function formatDateLabel(dateStr) {
    if (!dateStr) return ''
    const parts = String(dateStr).split('-')
    if (parts.length === 3) {
      return `${parts[1]}-${parts[2]}`
    }
    return String(dateStr).slice(-5)
  }

  function formatTooltipDate(dateStr) {
    if (!dateStr) return ''
    return String(dateStr)
  }

  const dataCount = xAxis.length
  // 密集数据（>14个点）时旋转标签，避免重叠
  const isDense = dataCount > 14
  const rotate = isDense ? 35 : 0
  // 旋转模式下需要更大的底部空间
  const bottomMargin = isDense ? 90 : 72
  const labelInterval = dataCount <= 7 ? 0 : dataCount <= 14 ? 1 : Math.floor(dataCount / 7)

  const series = seriesData.map((item, index) => ({
    name: legend[index] || item.name || `Series ${index + 1}`,
    type: 'line',
    data: item.data || item,
    smooth: true,
    connectNulls: true,
    showSymbol: false,
    symbol: 'circle',
    symbolSize: 6,
    z: 2,
    lineStyle: {
      width: 2.5
    },
    areaStyle: {
      opacity: 0.06,
      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: colors[index % colors.length] },
        { offset: 1, color: colors[index % colors.length] + '00' }
      ])
    },
    itemStyle: {
      color: colors[index % colors.length],
      borderWidth: 2,
      borderColor: '#fff'
    },
    emphasis: {
      scale: true,
      focus: 'series',
      showSymbol: true,
      z: 10,
      lineStyle: {
        width: 3.5
      },
      itemStyle: {
        borderWidth: 2,
        borderColor: '#fff',
        shadowBlur: 6,
        shadowColor: 'rgba(0,0,0,0.15)'
      }
    }
  }))

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
        label: {
          show: false
        },
        z: 0
      },
      formatter: function(params) {
        if (!params || !params.length) return ''
        const dateStr = formatTooltipDate(params[0].axisValue)
        let html = `<div style="font-weight:600;margin-bottom:8px;font-size:13px;color:${textColor}">${dateStr}</div>`
        params.forEach(p => {
          const val = p.value != null ? Number(p.value).toFixed(1) : '--'
          html += `<div style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:12px">
            <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
            <span style="color:${subTextColor};flex:1">${p.seriesName}</span>
            <span style="color:${textColor};font-weight:600">${val}</span>
          </div>`
        })
        return html
      }
    },
    legend: {
      data: legend,
      bottom: 4,
      left: 'center',
      icon: 'circle',
      itemWidth: 7,
      itemHeight: 7,
      itemGap: 14,
      symbolKeepAspect: true,
      padding: [2, 8, 2, 8],
      textStyle: {
        color: subTextColor,
        fontSize: 11,
        fontWeight: 400,
        lineHeight: 16
      },
      type: 'scroll',
      orient: 'horizontal',
      pageButtonItemGap: 4,
      pageIconSize: 10,
      pageTextStyle: {
        color: subTextColor,
        fontSize: 10
      }
    },
    grid: {
      top: 20,
      left: 48,
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
        lineStyle: {
          color: gridColor,
          width: 1
        }
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: subTextColor,
        fontSize: 11,
        margin: 12,
        showMaxLabel: true,
        showMinLabel: true,
        hideOverlap: true,
        interval: labelInterval,
        align: isDense ? 'right' : 'center',
        rotate: rotate,
        formatter: formatDateLabel
      }
    },
    yAxis: {
      type: 'value',
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      axisLabel: {
        color: subTextColor,
        fontSize: 11,
        margin: 10,
        showMaxLabel: true,
        showMinLabel: true,
        formatter: (value) => Math.round(value)
      },
      splitLine: {
        lineStyle: {
          color: gridColor,
          width: 1,
          type: 'solid'
        }
      },
      min: (value) => Math.floor(value.min / 10) * 10,
      max: (value) => Math.ceil(value.max / 10) * 10
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        zoomLock: false,
        throttle: 50
      }
    ],
    series
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
  () => props.data,
  () => {
    nextTick(() => updateChart())
  },
  { deep: true }
)

watch(
  () => themeStore.isDark,
  () => {
    nextTick(() => {
      initChart()
    })
  }
)

onMounted(() => {
  nextTick(() => {
    requestAnimationFrame(() => {
      initChart()
    })
  })

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
})

defineExpose({
  resize: scheduleResize,
  getInstance: () => chartInstance
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-line-chart {
  width: 100%;
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  overflow: visible;
  padding: 8px 8px 8px 8px;
  box-sizing: border-box;
}

.chart-container {
  width: 100%;
  min-height: 320px;
}
</style>
