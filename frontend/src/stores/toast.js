import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toast', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref('info')
  const duration = ref(3000)

  function show(msg, options = {}) {
    message.value = msg
    type.value = options.type || 'info'
    duration.value = options.duration ?? 3000
    visible.value = true
  }

  function success(msg, duration) {
    show(msg, { type: 'success', duration })
  }

  function error(msg, duration) {
    show(msg, { type: 'error', duration: duration ?? 5000 })
  }

  function warning(msg, duration) {
    show(msg, { type: 'warning', duration })
  }

  function info(msg, duration) {
    show(msg, { type: 'info', duration })
  }

  function hide() {
    visible.value = false
  }

  return {
    visible,
    message,
    type,
    duration,
    show,
    success,
    error,
    warning,
    info,
    hide
  }
})
