import { defineStore } from 'pinia'
import { ref } from 'vue'

// Toast 节流配置：相同内容的提示在指定时间内只显示一次
const THROTTLE_MS = 10000 // 10秒节流

export const useToastStore = defineStore('toast', () => {
  const visible = ref(false)
  const message = ref('')
  const type = ref('info')
  const duration = ref(3000)

  // 节流状态记录
  let lastMessage = ''
  let lastType = ''
  let lastShowTime = 0

  function show(msg, options = {}) {
    const msgType = options.type || 'info'

    // 节流检查：相同内容+相同类型在节流时间内不重复显示
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

  // 清除节流缓存（用于需要强制显示的场景）
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
