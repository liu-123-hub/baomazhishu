<template>
  <div class="ios-metric-card ios-pressable" :class="{ 'has-icon': icon }">
    <div class="metric-header">
      <div v-if="icon" class="metric-icon" :style="{ backgroundColor: iconBgColor }">
        <span class="icon-emoji">{{ icon }}</span>
      </div>
      <span class="metric-title">{{ title }}</span>
    </div>
    <div class="metric-body">
      <span class="metric-value" :style="{ color: resolvedColor }">{{ displayValue }}</span>
      <span v-if="subValue" class="metric-sub" :class="subValueClass">
        <span v-if="trend" class="trend-icon">{{ trendIcon }}</span>
        {{ displaySubValue }}
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  value: {
    type: [String, Number],
    default: '--'
  },
  subValue: {
    type: [String, Number],
    default: null
  },
  color: {
    type: String,
    default: null
  },
  icon: {
    type: String,
    default: null
  },
  trend: {
    type: String,
    default: null
  }
})

const colorMap = {
  blue: 'var(--ios-blue)',
  green: 'var(--ios-green)',
  red: 'var(--ios-red)',
  orange: 'var(--ios-orange)',
  purple: 'var(--ios-purple)',
  teal: 'var(--ios-teal)',
  pink: 'var(--ios-pink)',
  indigo: 'var(--ios-indigo)'
}

const resolvedColor = computed(() => {
  if (!props.color) return 'var(--ios-label-primary)'
  if (colorMap[props.color]) return colorMap[props.color]
  return props.color
})

const iconBgColor = computed(() => {
  if (!props.color) return 'var(--ios-fill-primary)'
  const baseColor = resolvedColor.value
  
  
  return `color-mix(in srgb, ${baseColor} 12%, transparent)`
})

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') return '--'
  const num = Number(props.value)
  if (!Number.isNaN(num) && typeof props.value === 'number') {
    if (Number.isInteger(num)) return num.toString()
    return num.toFixed(2).replace(/\.?0+$/, '')
  }
  return props.value
})

const displaySubValue = computed(() => {
  if (props.subValue === null || props.subValue === undefined) return ''
  const num = Number(props.subValue)
  if (!Number.isNaN(num)) {
    const sign = num > 0 ? '+' : ''
    return `${sign}${num.toFixed(2)}%`
  }
  return props.subValue
})

const subValueClass = computed(() => {
  const num = Number(props.subValue)
  if (Number.isNaN(num)) return 'neutral'
  if (num > 0) return 'positive'
  if (num < 0) return 'negative'
  return 'neutral'
})

const trendIcon = computed(() => {
  if (props.trend === 'up') return '↑'
  if (props.trend === 'down') return '↓'
  if (props.trend === 'flat') return '→'
  const num = Number(props.subValue)
  if (!Number.isNaN(num)) {
    if (num > 0) return '↑'
    if (num < 0) return '↓'
  }
  return ''
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-metric-card {
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  padding: var(--ios-spacing-lg);
  transition: all var(--ios-duration-normal) var(--ios-ease);
  animation: ios-fade-in var(--ios-duration-normal) var(--ios-ease-out);

  &.has-icon {
    .metric-header {
      margin-bottom: var(--ios-spacing-md);
    }
  }
}

.metric-header {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  margin-bottom: var(--ios-spacing-sm);
}

.metric-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--ios-radius-md);
  flex-shrink: 0;
}

.icon-emoji {
  font-size: 16px;
  line-height: 1;
}

.metric-title {
  font-size: var(--ios-text-sm);
  font-weight: 500;
  color: var(--ios-label-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.metric-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-value {
  font-size: var(--ios-text-3xl);
  font-weight: 700;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.03em;
}

.metric-sub {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--ios-text-sm);
  font-weight: 500;
  font-variant-numeric: tabular-nums;

  &.positive {
    color: var(--ios-red);
  }

  &.negative {
    color: var(--ios-green);
  }

  &.neutral {
    color: var(--ios-label-secondary);
  }
}

.trend-icon {
  font-size: 10px;
  line-height: 1;
}

@include mobile {
  .ios-metric-card {
    padding: var(--ios-spacing-md);
  }

  .metric-value {
    font-size: var(--ios-text-2xl);
  }
}
</style>
