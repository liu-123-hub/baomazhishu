import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(false)

  const STORAGE_KEY = 'mom-index-theme'

  function initTheme() {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved) {
      isDark.value = saved === 'dark'
    } else {
      isDark.value = window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    applyTheme()
  }

  function applyTheme() {
    const root = document.documentElement
    if (isDark.value) {
      root.classList.add('dark')
      root.setAttribute('data-theme', 'dark')
    } else {
      root.classList.remove('dark')
      root.removeAttribute('data-theme')
    }
  }

  function toggleTheme() {
    isDark.value = !isDark.value
    localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    applyTheme()
  }

  watch(isDark, () => {
    applyTheme()
  })

  return {
    isDark,
    initTheme,
    toggleTheme
  }
})
