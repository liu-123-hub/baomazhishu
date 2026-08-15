import { defineStore } from 'pinia'
import { ref } from 'vue'


const THROTTLE_MS = 10000 

export const useToastStore = defineStore('toast', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref('info')
  const duration = ref(3000)

  
  let lastMessage = ''
  let lastType = ''
  let lastShowTime = 0

  function show(msg, options = {}) {
    const msgType = options.type || 'info'

    
    const now = Date.now()
    if (msg === lastMessage && msgType === lastType && (now - lastShowTime) < THROTTLE_MS) {
      return
    }

    lastMessage = msg
    lastType = msgType
    lastShowTime = now

    message.value = msg
    type.value = msgType
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

  
  function clearThrottle() {
    lastMessage = ''
    lastType = ''
    lastShowTime = 0
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
    hide,
    clearThrottle
  }
})
