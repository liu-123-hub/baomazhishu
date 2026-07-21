/**
 * 跨平台核心适配层
 * 统一封装 Web / Tauri / Electron / Mobile 四端能力
 */

const PLATFORM_TYPES = {
  WEB: 'web',
  TAURI: 'tauri',
  ELECTRON: 'electron',
  MOBILE: 'mobile',
  CAPACITOR: 'capacitor'
}

const OS_TYPES = {
  WINDOWS: 'windows',
  MACOS: 'macos',
  LINUX: 'linux',
  IOS: 'ios',
  ANDROID: 'android',
  UNKNOWN: 'unknown'
}

let currentPlatform = PLATFORM_TYPES.WEB
let currentOS = OS_TYPES.UNKNOWN
let nativeApis = null

function detectPlatform() {
  if (typeof window !== 'undefined') {
    if (window.__TAURI__) {
      return PLATFORM_TYPES.TAURI
    }
    if (window.electronAPI || (window.process && window.process.versions && window.process.versions.electron)) {
      return PLATFORM_TYPES.ELECTRON
    }
    if (window.Capacitor && window.Capacitor.isNativePlatform()) {
      return PLATFORM_TYPES.CAPACITOR
    }
    const ua = navigator.userAgent.toLowerCase()
    if (/mobile|android|iphone|ipad|ipod/i.test(ua)) {
      return PLATFORM_TYPES.MOBILE
    }
  }
  return PLATFORM_TYPES.WEB
}

function detectOS() {
  if (typeof navigator !== 'undefined') {
    const ua = navigator.userAgent.toLowerCase()
    if (ua.includes('win')) return OS_TYPES.WINDOWS
    if (ua.includes('mac')) return OS_TYPES.MACOS
    if (ua.includes('linux')) return OS_TYPES.LINUX
    if (ua.includes('iphone') || ua.includes('ipad') || ua.includes('ipod')) return OS_TYPES.IOS
    if (ua.includes('android')) return OS_TYPES.ANDROID
  }
  return OS_TYPES.UNKNOWN
}

function isTouchDevice() {
  if (typeof window !== 'undefined') {
    return 'ontouchstart' in window || navigator.maxTouchPoints > 0
  }
  return false
}

function initPlatform() {
  currentPlatform = detectPlatform()
  currentOS = detectOS()
  return {
    platform: currentPlatform,
    os: currentOS,
    isTouch: isTouchDevice()
  }
}

async function loadNativeApis() {
  if (currentPlatform === PLATFORM_TYPES.TAURI) {
    try {
      const tauriApis = await import('./tauri.js')
      nativeApis = tauriApis.default
    } catch (e) {
      nativeApis = createFallbackApis()
    }
  } else if (currentPlatform === PLATFORM_TYPES.ELECTRON) {
    try {
      const electronApis = await import('./electron.js')
      nativeApis = electronApis.default
    } catch (e) {
      nativeApis = createFallbackApis()
    }
  } else if (currentPlatform === PLATFORM_TYPES.CAPACITOR) {
    try {
      const capApis = await import('./capacitor.js')
      nativeApis = capApis.default
    } catch (e) {
      nativeApis = createFallbackApis()
    }
  } else {
    nativeApis = createFallbackApis()
  }
  return nativeApis
}

function createFallbackApis() {
  return {
    async readFile() { return null },
    async writeFile() { return false },
    async showNotification(title, body) {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body })
        return true
      }
      return false
    },
    async requestNotificationPermission() {
      if ('Notification' in window) {
        const permission = await Notification.requestPermission()
        return permission === 'granted'
      }
      return false
    },
    async setTitle(title) { document.title = title },
    async minimize() {},
    async maximize() {},
    async close() {},
    async isMaximized() { return false },
    async openExternal(url) { window.open(url, '_blank') },
    async openUrl(url) { window.open(url, '_blank') },
    async saveData(key, value) {
      try { localStorage.setItem(`mom_${key}`, JSON.stringify(value)); return true } catch { return false }
    },
    async loadData(key, defaultValue = null) {
      try {
        const data = localStorage.getItem(`mom_${key}`)
        return data ? JSON.parse(data) : defaultValue
      } catch { return defaultValue }
    },
    async saveFile(content, filename) {
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    },
    async readFileDialog() {
      return new Promise((resolve) => {
        const input = document.createElement('input')
        input.type = 'file'
        input.accept = '.json,.txt,.csv'
        input.onchange = (e) => {
          const file = e.target.files?.[0]
          if (!file) return resolve(null)
          const reader = new FileReader()
          reader.onload = (ev) => resolve({ name: file.name, content: ev.target.result })
          reader.readAsText(file)
        }
        input.click()
      })
    },
    async getAppVersion() { return '2.0.0-web' },
    async getSystemInfo() {
      return { platform: currentPlatform, os: currentOS, userAgent: navigator.userAgent }
    },
    showDevTools() {},
    reload() { location.reload() }
  }
}

const platform = {
  async init() {
    initPlatform()
    return loadNativeApis()
  },
  get type() { return currentPlatform },
  get os() { return currentOS },
  get isWeb() { return currentPlatform === PLATFORM_TYPES.WEB },
  get isTauri() { return currentPlatform === PLATFORM_TYPES.TAURI },
  get isElectron() { return currentPlatform === PLATFORM_TYPES.ELECTRON },
  get isDesktop() { return currentPlatform === PLATFORM_TYPES.TAURI || currentPlatform === PLATFORM_TYPES.ELECTRON },
  get isMobile() { return currentPlatform === PLATFORM_TYPES.MOBILE || currentPlatform === PLATFORM_TYPES.CAPACITOR },
  get isCapacitor() { return currentPlatform === PLATFORM_TYPES.CAPACITOR },
  get isTouch() { return isTouchDevice() },
  get apis() { return nativeApis || createFallbackApis() },
  PLATFORM_TYPES,
  OS_TYPES
}

export default platform
export { PLATFORM_TYPES, OS_TYPES }
