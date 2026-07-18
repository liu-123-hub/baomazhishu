<template>
  <BaseChart
    :option="chartOption"
    :width="width"
    :height="height"
  />
</template>

<script setup>
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

const GAUGE_COLORS = [
  [0.2, '#64748b'],
  [0.4, '#22c55e'],
  [0.6, '#f59e0b'],
  [0.8, '#ef4444'],
  [1, '#dc2626']
]

const props = defineProps({
  value: {
    type: Number,
    default: 0
  },
  name: {
    type: String,
    default: '指数'
  },
  max: {
    type: Number,
    default: 100
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '250px'
  }
})

const chartOption = computed(() => {
  const color = getGaugeColor(props.value)

  return {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    series: [
      {
        type: 'gauge',
        center: ['50%', '60%'],
        radius: '85%',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: props.max,
        splitNumber: 10,
        itemStyle: {
          color: color,
          shadowColor: color,
          // 降低阴影半径，减少指针动画时的重绘
          shadowBlur: 6
        },
        progress: {
          show: true,
          roundCap: true,
          width: 10
        },
        pointer: {
          icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
          length: '55%',
          width: 8,
          offsetCenter: [0, '-5%'],
          itemStyle: {
            color: color
          }
        },
        axisLine: {
          roundCap: true,
          lineStyle: {
            width: 10,
            color: GAUGE_COLORS
          }
        },
        axisTick: {
          splitNumber: 2,
          lineStyle: {
            width: 1,
            color: 'rgba(248, 250, 252, 0.25)'
          }
        },
        splitLine: {
          length: 8,
          lineStyle: {
            width: 2,
            color: 'rgba(248, 250, 252, 0.4)'
          }
        },
        axisLabel: {
          distance: 18,
          color: 'rgba(248, 250, 252, 0.5)',
          fontSize: 10
        },
        title: {
          offsetCenter: [0, '30%'],
          fontSize: 13,
          color: 'rgba(248, 250, 252, 0.6)'
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '0%'],
          fontSize: 30,
          fontWeight: 'bold',
          color: color,
          formatter: (value) => Number(value).toFixed(2)
        },
        data: [
          {
            value: props.value,
            name: props.name
          }
        ]
      }
    ]
  }
})

function getGaugeColor(value) {
  if (value < 20) return '#64748b'
  if (value < 40) return '#22c55e'
  if (value < 60) return '#f59e0b'
  if (value < 80) return '#ef4444'
  return '#dc2626'
}
</script>
