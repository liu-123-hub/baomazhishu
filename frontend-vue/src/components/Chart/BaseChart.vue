<template>
  <div ref="chartRef" :style="{ width: width, height: height }" class="chart-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick, computed } from 'vue'
import * as echarts from 'echarts'
import { useReducedMotion } from '@/composables/useReducedMotion.js'

const props = defineProps({
  option: {
    type: Object,
    default: () => ({})
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '300px'
  },
  theme: {
    type: String,
    default: 'dark'
  }
})

const emit = defineEmits(['click', 'ready'])

const chartRef = ref(null)
let chartInstance = null
let rafId = null
let resizeObserver = null
let isUpdating = false

// 检测用户是否偏好减少动画
const prefersReducedMotion = useReducedMotion()

// 根据辅助功能设置合并图表配置
const mergedOption = computed(() => ({
  // 默认性能优化：大数据集自动跳过动画；更新动画保持轻量
  animationThreshold: 2000,
  animationDurationUpdate: 300,
  ...props.option,
  animation: prefersReducedMotion.value ? false : (props.option.animation ?? true)
}))

function initChart() {
  if (!chartRef.value) return

  // 避免重复初始化
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value, props.theme)
  // 首次 setOption 使用 notMerge=true 确保完整渲染，启用 lazyUpdate 避免阻塞主线程
  chartInstance.setOption(mergedOption.value, { notMerge: true, lazyUpdate: true })

  chartInstance.on('click', (params) => {
    emit('click', params)
  })

  emit('ready', chartInstance)
}

function updateChart() {
  if (!chartInstance) return
  // 使用 rAF 调度，避免连续数据变更导致重复 setOption
  if (isUpdating) return
  isUpdating = true
  rafId = requestAnimationFrame(() => {
    rafId = null
    isUpdating = false
    if (!chartInstance) return
    // 差异更新，不替换整个配置，提升性能
    chartInstance.setOption(mergedOption.value, { notMerge: false, lazyUpdate: true })
  })
}

function scheduleResize() {
  if (rafId) return
  rafId = requestAnimationFrame(() => {
    rafId = null
    chartInstance?.resize()
  })
}

watch(
  () => props.option,
  () => {
    nextTick(() => {
      updateChart()
    })
  },
  { deep: true }
)

onMounted(() => {
  // 使用 requestAnimationFrame 替代 setTimeout，在浏览器准备好渲染时初始化
  rafId = requestAnimationFrame(() => {
    rafId = null
    initChart()
  })

  // ResizeObserver 优先于 window resize；两者都通过 rAF 调度 resize，防止布局抖动
  if (window.ResizeObserver && chartRef.value) {
    resizeObserver = new ResizeObserver(() => {
      scheduleResize()
    })
    resizeObserver.observe(chartRef.value)
  } else {
    window.addEventListener('resize', scheduleResize)
  }
})

onUnmounted(() => {
  if (rafId) {
    cancelAnimationFrame(rafId)
    rafId = null
  }
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
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
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 0;
  // 隔离图表尺寸变化对父级布局的影响
  contain: layout;
}
</style>
