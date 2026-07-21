<template>
  <div class="ios-segment-control">
    <button
      v-for="(option, index) in resolvedOptions"
      :key="index"
      type="button"
      class="segment-item"
      :class="{ active: modelValue === option.value || modelValue === option }"
      @click="handleSelect(option)"
    >
      <span class="segment-label">{{ option.label || option }}</span>
    </button>
    <div class="segment-indicator" :style="indicatorStyle"></div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  options: {
    type: Array,
    required: true
  },
  modelValue: {
    type: [String, Number],
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const resolvedOptions = computed(() => {
  return props.options.map(opt => {
    if (typeof opt === 'string' || typeof opt === 'number') {
      return { label: opt, value: opt }
    }
    return opt
  })
})

const activeIndex = computed(() => {
  const idx = resolvedOptions.value.findIndex(
    opt => opt.value === props.modelValue || opt.label === props.modelValue
  )
  return idx >= 0 ? idx : 0
})

const count = computed(() => resolvedOptions.value.length)

const PADDING = 2

const indicatorStyle = computed(() => {
  const n = count.value
  if (n === 0) return {}
  const idx = activeIndex.value
  return {
    width: `calc((100% - ${PADDING * 2}px) / ${n})`,
    transform: `translateX(${idx * 100}%)`
  }
})

function handleSelect(option) {
  const value = option.value !== undefined ? option.value : option
  emit('update:modelValue', value)
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-segment-control {
  position: relative;
  display: inline-flex;
  align-items: center;
  background: var(--ios-fill-primary);
  border-radius: var(--ios-radius-md);
  padding: 2px;
  gap: 0;
  user-select: none;
  -webkit-user-select: none;
  min-width: 240px;
  flex-shrink: 0;
}

.segment-item {
  position: relative;
  z-index: 1;
  flex: 1 1 0;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 30px;
  padding: 0 12px;
  border-radius: calc(var(--ios-radius-md) - 2px);
  font-size: var(--ios-text-sm);
  font-weight: 500;
  color: var(--ios-label-secondary);
  transition: color var(--ios-duration-fast) var(--ios-ease);
  cursor: pointer;
  white-space: nowrap;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  -webkit-tap-highlight-color: transparent;

  &.active {
    color: var(--ios-label-primary);
  }

  @media (hover: hover) {
    &:not(.active):hover {
      color: var(--ios-label-primary);
    }
  }

  &:active {
    opacity: 0.7;
  }
}

.segment-label {
  overflow: hidden;
  text-overflow: clip;
  flex-shrink: 1;
  min-width: 0;
  line-height: 1;
  white-space: nowrap;
}

.segment-indicator {
  position: absolute;
  top: 2px;
  left: 2px;
  bottom: 2px;
  background: var(--ios-bg-secondary);
  border-radius: calc(var(--ios-radius-md) - 2px);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.06);
  transition: transform var(--ios-duration-normal) var(--ios-spring),
              width var(--ios-duration-normal) var(--ios-spring);
  pointer-events: none;
}

@include mobile {
  .ios-segment-control {
    min-width: 220px;
  }

  .segment-item {
    height: 32px;
    font-size: var(--ios-text-base);
    padding: 0 10px;
  }
}
</style>
