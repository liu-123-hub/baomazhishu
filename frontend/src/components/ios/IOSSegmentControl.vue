<template>
  <div 
    class="ios-segment-control" 
    :class="{ 'many-items': resolvedOptions.length > 4 }"
    role="tablist"
    :aria-label="ariaLabel"
    @keydown="handleKeydown"
  >
    <button
      v-for="(option, index) in resolvedOptions"
      :key="index"
      type="button"
      class="segment-item"
      :class="{ active: isActive(option) }"
      :aria-selected="isActive(option)"
      :tabindex="isActive(option) ? 0 : -1"
      role="tab"
      :aria-label="option.label || option"
      @click="handleSelect(option)"
      @focus="handleFocus(index)"
    >
      <span class="segment-label">{{ option.label || option }}</span>
    </button>
    <div class="segment-indicator" :style="indicatorStyle" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

const props = defineProps({
  options: {
    type: Array,
    required: true
  },
  modelValue: {
    type: [String, Number],
    default: null
  },
  full: {
    type: Boolean,
    default: false
  },
  ariaLabel: {
    type: String,
    default: '选项卡切换'
  }
})

const emit = defineEmits(['update:modelValue'])

const focusedIndex = ref(0)

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

function isActive(option) {
  return props.modelValue === option.value || props.modelValue === option || props.modelValue === option.label
}

function handleSelect(option) {
  const value = option.value !== undefined ? option.value : option
  emit('update:modelValue', value)
}

function handleFocus(index) {
  focusedIndex.value = index
}

function handleKeydown(e) {
  const n = count.value
  if (n === 0) return

  let newIndex = focusedIndex.value

  switch (e.key) {
    case 'ArrowLeft':
      e.preventDefault()
      newIndex = (focusedIndex.value - 1 + n) % n
      break
    case 'ArrowRight':
      e.preventDefault()
      newIndex = (focusedIndex.value + 1) % n
      break
    case 'Home':
      e.preventDefault()
      newIndex = 0
      break
    case 'End':
      e.preventDefault()
      newIndex = n - 1
      break
    case 'Enter':
    case ' ':
      e.preventDefault()
      handleSelect(resolvedOptions.value[focusedIndex.value])
      return
    default:
      return
  }

  focusedIndex.value = newIndex
  const buttons = e.currentTarget.querySelectorAll('.segment-item')
  if (buttons[newIndex]) {
    nextTick(() => {
      buttons[newIndex].focus({ preventScroll: true })
    })
  }
}

watch(activeIndex, (newActive) => {
  focusedIndex.value = newActive
})
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
  min-width: 200px;
  flex-shrink: 0;
  overflow: hidden;

  &.many-items {
    min-width: 0;
    width: 100%;
    max-width: 100%;
  }
}

.segment-item {
  position: relative;
  z-index: 1;
  flex: 1 1 0;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 36px;
  padding: 0 12px;
  border-radius: calc(var(--ios-radius-md) - 2px);
  font-size: var(--ios-text-sm);
  font-weight: 500;
  color: var(--ios-label-secondary);
  transition: color var(--ios-duration-fast) var(--ios-ease);
  cursor: pointer;
  white-space: nowrap;
  min-width: 0;
  overflow: hidden;
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

  &:focus-visible {
    @include ios-focus-ring;
    z-index: 2;
  }
}

.many-items .segment-item {
  padding: 0 4px;
  font-size: 12px;
  height: 32px;
}

.segment-label {
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
  min-width: 0;
  max-width: 100%;
  line-height: 1.2;
  white-space: nowrap;
  text-align: center;
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
    min-width: 180px;
  }

  .ios-segment-control.many-items {
    min-width: 0;
    width: 100%;
  }

  .segment-item {
    height: 32px;
    font-size: var(--ios-text-sm);
    padding: 0 8px;
  }

  .many-items .segment-item {
    padding: 0 3px;
    font-size: 11px;
    height: 32px;
  }
}

@media (max-width: 360px) {
  .many-items .segment-item {
    padding: 0 2px;
    font-size: 10px;
    height: 30px;
  }

  .segment-label {
    letter-spacing: -0.02em;
  }
}
</style>
