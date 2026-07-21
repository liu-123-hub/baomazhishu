import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useSystemStore = defineStore('system', () => {
  const platformType = ref(null)
  const os = ref('unknown')
  const isDesktop = ref(false)
  const isMobile = ref(false)
  const isMaximized = ref(false)
  const nativeApis = ref(null)

  // 真实网络连接状态（浏览器/系统层面）
  const isOnline = ref(true)

  function setPlatformInfo(info) {
    platformType.value = info.platform
    os.value = info.os
    isDesktop.value = info.isDesktop
    isMobile.value = info.isMobile
    nativeApis.value = info.apis
  }

  function setMaximized(value) {
    isMaximized.value = value
  }

  /**
   * 初始化真实网络状态检测
   * 使用 navigator.onLine + online/offline 事件，准确反映网络连接情况
   * 与后端服务是否可用无关
   */
  function initNetworkStatus() {
    if (typeof navigator !== 'undefined') {
      isOnline.value = navigator.onLine
    }
    if (typeof window !== 'undefined') {
      window.addEventListener('online', handleOnline)
      window.addEventListener('offline', handleOffline)
    }
  }

  function handleOnline() {
    isOnline.value = true
  }

  function handleOffline() {
    isOnline.value = false
  }

  async function minimizeWindow() {
    if (nativeApis.value?.minimize) {
      await nativeApis.value.minimize()
    }
  }

  async function maximizeWindow() {
    if (nativeApis.value?.maximize) {
      await nativeApis.value.maximize()
      const max = await nativeApis.value.isMaximized?.()
      isMaximized.value = !!max
    }
  }

  async function closeWindow() {
    if (nativeApis.value?.close) {
      await nativeApis.value.close()
    }
  }

  return {
    platformType,
    os,
    isDesktop,
    isMobile,
    isMaximized,
    nativeApis,
    isOnline,
    setPlatformInfo,
    setMaximized,
    initNetworkStatus,
    minimizeWindow,
    maximizeWindow,
    closeWindow
  }
})
