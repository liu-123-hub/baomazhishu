<template>
  <Teleport to="body">
    <Transition name="toast">
      <div v-if="visible" class="ios-toast-container" role="alert" aria-live="polite">
        <div class="ios-toast" :class="typeClass">
          <span class="toast-icon">{{ iconText }}</span>
          <span class="toast-message">{{ message }}</span>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  message: { type: String, default: '' },
  type: { type: String, default: 'info', validator: v => ['info', 'success', 'warning', 'error'].includes(v) },
  duration: { type: Number, default: 3000 }
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
let hideTimer = null

const typeClass = computed(() => `toast-${props.type}`)
const iconText = computed(() => {
  const icons = { info: 'ℹ️', success: '✅', warning: '⚠️', error: '❌' }
  return icons[props.type] || icons.info
})

function show() {
  if (hideTimer) clearTimeout(hideTimer)
  visible.value = true
  if (props.duration > 0) {
    hideTimer = setTimeout(hide, props.duration)
  }
}

function hide() {
  visible.value = false
  emit('update:modelValue', false)
}

watch(() => props.modelValue, (val) => {
  if (val) show()
  else hide()
}, { immediate: true })

defineExpose({ show, hide })
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-toast-container {
  position: fixed;
  top: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px) + var(--ios-spacing-lg));
  left: 50%;
  transform: translateX(-50%);
  z-index: 9999;
  pointer-events: none;
}

.ios-toast {
  display: inline-flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  padding: var(--ios-spacing-md) var(--ios-spacing-lg);
  background: var(--ios-bg-elevated);
  border-radius: var(--ios-radius-lg);
  box-shadow: var(--ios-shadow-xl);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  pointer-events: auto;
  max-width: calc(100vw - 32px);
}

.toast-icon {
  font-size: var(--ios-text-lg);
  line-height: 1;
  flex-shrink: 0;
}

.toast-message {
  font-size: var(--ios-text-sm);
  font-weight: 500;
  color: var(--ios-label-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toast-success { border-left: 3px solid var(--ios-green); }
.toast-warning { border-left: 3px solid var(--ios-orange); }
.toast-error { border-left: 3px solid var(--ios-red); }
.toast-info { border-left: 3px solid var(--ios-blue); }

.toast-enter-active,
.toast-leave-active {
  transition: all var(--ios-duration-normal) var(--ios-spring);
}

.toast-enter-from {
  opacity: 0;
  transform: translate(-50%, -20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translate(-50%, -10px);
}

@include mobile {
  .ios-toast-container {
    top: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px) + var(--ios-spacing-md));
    width: calc(100% - 32px);
  }

  .ios-toast {
    width: 100%;
    justify-content: center;
  }
}
</style>
