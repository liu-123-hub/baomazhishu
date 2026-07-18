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
import BaseChart from './BaseChart.vue'

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
  categories: {
    type: Array,
    default: () => []
  },
  seriesData: {
    type: Array,
    default: () => []
  },
  title: {
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
  horizontal: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['bar-click'])

const chartOption = computed(() => {
  const series = props.seriesData.map((item, index) => ({
    name: item.name,
    type: 'bar',
    data: item.data,
    barWidth: item.barWidth || (props.horizontal ? '45%' : '32%'),
    barGap: '20%',
    // 大数据量时分块渲染，降低主线程阻塞
    progressive: 200,
    progressiveThreshold: 300,
    itemStyle: {
      color: item.color || getChartColor(index),
      borderRadius: item.borderRadius || (props.horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0])
    },
    emphasis: {
      itemStyle: {
        // 降低阴影半径，减少高亮时的重绘开销
        shadowBlur: 8,
        shadowColor: item.color || getChartColor(index)
      }
    }
  }))

  const axisConfig = {
    type: 'category',
    data: props.categories,
    axisLine: {
      lineStyle: {
        color: CHART_AXIS_LINE
      }
    },
    axisLabel: {
      color: CHART_TEXT_TERTIARY,
      fontSize: 11
    },
    axisTick: {
      show: false
    }
  }

  const valueAxisConfig = {
    type: 'value',
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
  }

  return {
    animationDuration: 600,
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
        type: 'shadow',
        shadowStyle: {
          color: 'rgba(14, 165, 233, 0.1)'
        }
      }
    },
    legend: {
      data: props.seriesData.map(s => s.name),
      textStyle: {
        color: CHART_TEXT_SECONDARY,
        fontSize: 12
      },
      top: 0,
      right: 0,
      show: props.seriesData.length > 1
    },
    grid: {
      left: props.horizontal ? '2%' : '2%',
      right: props.horizontal ? '8%' : '3%',
      bottom: '2%',
      top: 32,
      containLabel: true
    },
    xAxis: props.horizontal ? valueAxisConfig : axisConfig,
    yAxis: props.horizontal ? axisConfig : valueAxisConfig,
    series
  }
})

function getChartColor(index) {
  return CHART_COLORS[index % CHART_COLORS.length]
}

function handleClick(params) {
  emit('bar-click', params)
}
</script>
