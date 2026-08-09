<template>
  <div class="ios-sector-list">
    <div v-if="title" class="list-header">
      <span class="list-title">{{ title }}</span>
      <span v-if="modelValue && modelValue.length > 0" class="list-count">
        已选 {{ modelValue.length }}
      </span>
    </div>
    <div class="sector-items">
      <div
        v-for="sector in sectors"
        :key="sector.code || sector.name"
        class="sector-item ios-pressable"
        :class="{ active: isSelected(sector), 'no-data': sector.value == null }"
        role="button"
        :tabindex="sector.value == null ? -1 : 0"
        :aria-pressed="isSelected(sector)"
        :aria-label="`${sector.name}，指数 ${formatValue(sector.value)}`"
        @click="handleSelect(sector)"
        @keydown.enter.prevent="handleSelect(sector)"
        @keydown.space.prevent="handleSelect(sector)"
      >
        <span class="sector-dot" :style="{ backgroundColor: sector.color }"></span>
        <span class="sector-name">{{ sector.name }}</span>
        <span class="sector-value" :class="getValueClass(sector.value)">
          {{ formatValue(sector.value) }}
        </span>
        <button v-if="navigable" class="sector-chevron ios-touch-target" @click.stop="handleNavigate(sector)">
          <svg width="8" height="14" viewBox="0 0 8 14" fill="none">
            <path d="M1 1L7 7L1 13" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  sectors: {
    type: Array,
    required: true
  },
  modelValue: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: ''
  },
  multiple: {
    type: Boolean,
    default: true
  },
  navigable: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'select', 'navigate'])

function isSelected(sector) {
  const code = sector.code || sector.name
  return props.modelValue.includes(code)
}

function handleSelect(sector) {
  const code = sector.code || sector.name
  let newValue
  if (props.multiple) {
    if (isSelected(sector)) {
      if (props.modelValue.length <= 1) return
      newValue = props.modelValue.filter(v => v !== code)
    } else {
      newValue = [...props.modelValue, code]
    }
  } else {
    newValue = isSelected(sector) ? [] : [code]
  }
  emit('update:modelValue', newValue)
  emit('select', sector)
}

function handleNavigate(sector) {
  emit('navigate', sector)
}

function formatValue(value) {
  if (value === null || value === undefined || value === '') return '--'
  const num = Number(value)
  if (!Number.isNaN(num)) {
    return num.toFixed(2)
  }
  return value
}

function getValueClass(value) {
  if (value === null || value === undefined) return 'neutral'
  const num = Number(value)
  if (Number.isNaN(num)) return 'neutral'
  if (num >= 60) return 'hot'
  if (num >= 40) return 'warm'
  if (num >= 20) return 'cool'
  return 'cold'
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-sector-list {
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  overflow: hidden;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--ios-spacing-md) var(--ios-spacing-lg);
  border-bottom: 1px solid var(--ios-separator);
}

.list-title {
  font-size: var(--ios-text-sm);
  font-weight: 600;
  color: var(--ios-label-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.list-count {
  font-size: var(--ios-text-xs);
  color: var(--ios-label-tertiary);
  font-weight: 500;
}

.sector-items {
  max-height: 400px;
  overflow-y: auto;
  @include ios-scrollbar;
}

.sector-item {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  padding: var(--ios-spacing-md) var(--ios-spacing-lg);
  border-bottom: 1px solid var(--ios-separator);
  cursor: pointer;
  transition: all var(--ios-duration-fast) var(--ios-ease);
  border-left: 3px solid transparent;

  &:last-child {
    border-bottom: none;
  }

  &.active {
    background: var(--ios-fill-primary);
    border-left-color: var(--ios-blue);
  }

  &.no-data {
    opacity: 0.5;

    .sector-name {
      color: var(--ios-label-tertiary);
    }
  }

  &:focus-visible {
    outline: 2px solid var(--ios-blue);
    outline-offset: -2px;
  }
}

.sector-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.sector-name {
  flex: 1;
  font-size: var(--ios-text-base);
  font-weight: 500;
  color: var(--ios-label-primary);
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sector-value {
  font-size: var(--ios-text-sm);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;

  &.hot { color: var(--ios-red); }
  &.warm { color: var(--ios-orange); }
  &.cool { color: var(--ios-blue); }
  &.cold { color: var(--ios-label-secondary); }
  &.neutral { color: var(--ios-label-tertiary); }
}

.sector-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-left: var(--ios-spacing-xs);
  padding: 0;
  border: none;
  background: none;
  color: var(--ios-label-tertiary);
  cursor: pointer;
  border-radius: var(--ios-radius-md);
  flex-shrink: 0;
  transition: all var(--ios-duration-fast) var(--ios-ease);

  @media (hover: hover) {
    &:hover {
      background: var(--ios-fill-primary);
      color: var(--ios-label-secondary);
    }
  }

  &:active {
    background: var(--ios-fill-secondary);
    transform: scale(0.9);
  }
}

@include mobile {
  .sector-items {
    max-height: 300px;
  }

  .sector-item {
    padding: var(--ios-spacing-sm) var(--ios-spacing-md);
  }
}
</style>
