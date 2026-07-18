import { ref, onMounted, onUnmounted } from 'vue'

/**
 * 检测用户是否偏好减少动画（prefers-reduced-motion）
 * 用于在低端设备或辅助功能场景下关闭非必要动画，提升性能与可访问性
 */
export function useReducedMotion() {
  const prefersReducedMotion = ref(false)
  let mediaQuery = null

  const update = () => {
    prefersReducedMotion.value = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }

  onMounted(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    update()
    mediaQuery.addEventListener('change', update)
  })

  onUnmounted(() => {
    mediaQuery?.removeEventListener('change', update)
  })

  return prefersReducedMotion
}
