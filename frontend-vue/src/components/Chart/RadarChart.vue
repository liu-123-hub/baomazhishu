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

const CHART_TEXT_PRIMARY = '#f8fafc'
const CHART_TEXT_SECONDARY = 'rgba(248, 250, 252, 0.7)'
const CHART_BG_TOOLTIP = 'rgba(15, 23, 42, 0.95)'
const CHART_BORDER_TOOLTIP = 'rgba(14, 165, 233, 0.3)'

const props = defineProps({
  indicators: {
    type: Array,
    default: () => []
  },
  values: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  name: {
    type: String,
    default: '指数'
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '300px'
  },
  color: {
    type: String,
    default: '#0ea5e9'
  }
})

const emit = defineEmits(['radar-click'])

const chartOption = computed(() => {
  const color = props.color || '#0ea5e9'
  return {
    animationDuration: 600,
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
      backgroundColor: CHART_BG_TOOLTIP,
      borderColor: CHART_BORDER_TOOLTIP,
      textStyle: {
        color: CHART_TEXT_PRIMARY,
        fontSize: 12
      }
    },
    radar: {
      indicator: props.indicators,
      center: ['50%', '55%'],
      radius: '58%',
      axisName: {
        color: CHART_TEXT_SECONDARY,
        fontSize: 11
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(248, 250, 252, 0.1)'
        }
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(14, 165, 233, 0.02)',
            'rgba(14, 165, 233, 0.05)'
          ]
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(248, 250, 252, 0.15)'
        }
      }
    },
    series: [
      {
        name: props.name,
        type: 'radar',
        data: [
          {
            value: props.values,
            name: props.name,
            areaStyle: {
              color: hexToRgba(color, 0.25)
            },
            lineStyle: {
              color: color,
              width: 2
            },
            itemStyle: {
              color: color
            },
            symbol: 'circle',
            symbolSize: 4
          }
        ]
      }
    ]
  }
})

function hexToRgba(hex, alpha) {
  if (!hex || hex.length < 7) return `rgba(14, 165, 233, ${alpha})`
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

function handleClick(params) {
  emit('radar-click', params)
}
</script>
