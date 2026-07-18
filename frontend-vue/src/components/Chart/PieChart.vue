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
  data: {
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
  radius: {
    type: [String, Array],
    default: () => ['40%', '70%']
  },
  roseType: {
    type: [String, Boolean],
    default: false
  }
})

const emit = defineEmits(['slice-click'])

const chartOption = computed(() => {
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
      trigger: 'item',
      backgroundColor: CHART_BG_TOOLTIP,
      borderColor: CHART_BORDER_TOOLTIP,
      textStyle: {
        color: CHART_TEXT_PRIMARY,
        fontSize: 12
      },
      formatter: (params) => {
        const val = params.value != null ? Number(params.value).toFixed(2) : '--'
        return `${params.name}: <strong>${val}</strong> (${params.percent}%)`
      }
    },
    legend: {
      orient: 'vertical',
      right: 0,
      top: 'middle',
      textStyle: {
        color: CHART_TEXT_SECONDARY,
        fontSize: 11
      },
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 10
    },
    series: [
      {
        name: props.title,
        type: 'pie',
        radius: props.radius,
        center: ['34%', '55%'],
        roseType: props.roseType,
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: 'rgba(2, 6, 23, 0.8)',
          borderWidth: 2
        },
        label: {
          show: false
        },
        emphasis: {
          scaleSize: 6,
          label: {
            show: true,
            color: CHART_TEXT_PRIMARY,
            fontSize: 13,
            fontWeight: 'bold'
          },
          itemStyle: {
            // 降低阴影半径，减少高亮重绘开销
            shadowBlur: 10,
            shadowColor: 'rgba(14, 165, 233, 0.4)'
          }
        },
        labelLine: {
          show: false
        },
        data: props.data
      }
    ]
  }
})

function handleClick(params) {
  emit('slice-click', params)
}
</script>
