<template>
  <BaseChart
    :option="chartOption"
    :width="width"
    :height="height"
    @click="handleClick"
  />
</template>

<script setup>
import { computed } from 'vue'
import * as echarts from 'echarts'
import BaseChart from './BaseChart.vue'

// 统一图表色板
const CHART_COLORS = [
  '#0ea5e9', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4',
  '#a855f7', '#f472b6', '#fb923c', '#84cc16', '#60a5fa',
  '#f87171', '#34d399', '#fbbf24', '#a78bfa', '#fb7185'
]

const CHART_TEXT_PRIMARY = '#f8fafc'
const CHART_TEXT_SECONDARY = 'rgba(248, 250, 252, 0.7)'
const CHART_TEXT_TERTIARY = 'rgba(248, 250, 252, 0.55)'
const CHART_BG_TOOLTIP = 'rgba(15, 23, 42, 0.95)'
const CHART_BORDER_TOOLTIP = 'rgba(14, 165, 233, 0.3)'
const CHART_SPLIT_LINE = 'rgba(248, 250, 252, 0.06)'
const CHART_AXIS_LINE = 'rgba(248, 250, 252, 0.15)'

const props = defineProps({
  xAxisData: {
    type: Array,
    default: () => []
  },
  seriesData: {
    type: Array,
    default: () => []
  },
  legendData: {
    type: Array,
    default: () => []
  },
  nameMap: {
    type: Object,
    default: () => ({})
  },
  title: {
    type: String,
    default: ''
  },
  yAxisName: {
    type: String,
    default: ''
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '300px'
  },
  smooth: {
    type: Boolean,
    default: true
  },
  showArea: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['point-click'])

function formatName(name) {
  return props.nameMap[name] || name
}

const chartOption = computed(() => {
  const series = props.seriesData.map((item, index) => {
    const color = item.itemStyle?.color || getChartColor(index)
    const result = {
      name: formatName(item.name),
      type: 'line',
      smooth: props.smooth,
      data: item.data,
      lineStyle: {
        width: 2.5,
        color: color
      },
      itemStyle: {
        color: color
      },
      symbol: 'circle',
      symbolSize: 5,
      // 大数据量时分块渲染，降低主线程阻塞
      progressive: 300,
      progressiveThreshold: 500,
      emphasis: {
        focus: 'series',
        symbolSize: 8
      }
    }
    if (props.showArea) {
      result.areaStyle = {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: hexToRgba(color, 0.3) },
          { offset: 1, color: hexToRgba(color, 0.02) }
        ])
      }
    }
    return result
  })

  return {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    title: props.title ? {
      text: props.title,
      textStyle: {
        color: CHART_TEXT_PRIMARY,
        fontSize: 14,
        fontWeight: 500
      },
      left: 0,
      top: 0
    } : undefined,
    tooltip: {
      trigger: 'axis',
      backgroundColor: CHART_BG_TOOLTIP,
      borderColor: CHART_BORDER_TOOLTIP,
      textStyle: {
        color: CHART_TEXT_PRIMARY,
        fontSize: 12
      },
      formatter: (params) => {
        if (!Array.isArray(params)) return ''
        let html = `<div style="font-weight:600;margin-bottom:4px">${params[0].axisValue}</div>`
        params.forEach(p => {
          const marker = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:6px"></span>`
          const val = p.value != null ? Number(p.value).toFixed(2) : '--'
          html += `<div style="display:flex;align-items:center;justify-content:space-between;gap:16px">${marker}<span>${p.seriesName}</span><strong>${val}</strong></div>`
        })
        return html
      },
      axisPointer: {
        type: 'line',
        lineStyle: {
          color: 'rgba(14, 165, 233, 0.5)',
          type: 'dashed'
        }
      }
    },
    legend: {
      data: props.legendData.map(formatName),
      textStyle: {
        color: CHART_TEXT_SECONDARY,
        fontSize: 12
      },
      top: 0,
      right: 0,
      itemGap: 12,
      icon: 'roundRect',
      // 图例项超过 6 个时启用滚动翻页，避免多行堆叠挤压图表空间
      type: props.legendData.length > 6 ? 'scroll' : 'plain',
      pageIconColor: CHART_TEXT_SECONDARY,
      pageIconInactiveColor: CHART_TEXT_TERTIARY,
      pageTextStyle: {
        color: CHART_TEXT_SECONDARY,
        fontSize: 11
      },
      pageButtonItemGap: 8
    },
    grid: {
      left: '2%',
      right: '5%',
      bottom: '2%',
      top: 36,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: props.xAxisData,
      axisLine: {
        lineStyle: {
          color: CHART_AXIS_LINE
        }
      },
      axisLabel: {
        color: CHART_TEXT_TERTIARY,
        fontSize: 11
      },
      splitLine: {
        show: false
      }
    },
    yAxis: {
      type: 'value',
      name: props.yAxisName,
      nameTextStyle: {
        color: CHART_TEXT_TERTIARY,
        fontSize: 11
      },
      axisLine: {
        show: false
      },
      axisLabel: {
        color: CHART_TEXT_TERTIARY,
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: CHART_SPLIT_LINE
        }
      }
    },
    series
  }
})

function getChartColor(index) {
  return CHART_COLORS[index % CHART_COLORS.length]
}

function hexToRgba(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(14, 165, 233, ${alpha})`
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function handleClick(params) {
  emit('point-click', params)
}
</script>
