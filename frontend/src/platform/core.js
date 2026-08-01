/**
 * 平台适配层（Web 专用）
 *
 * 原跨平台（Tauri/Electron/Capacitor）打包方案已移除，仅保留 Web 端。
 * 仍保留 platform 接口与 OS/移动端 UA 识别，供 UI 层判断触屏/移动布局使用。
 */

const PLATFORM_TYPES = {
  WEB: 'web',
  MOBILE: 'mobile'
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
  // 仅通过 UA 区分移动端浏览器与桌面 Web，原生壳已移除
  if (typeof window !== 'undefined') {
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

// Web 端原生能力降级实现：通知/存储/文件/窗口等均使用浏览器 API
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
    nativeApis = createFallbackApis()
    return nativeApis
  },
  get type() { return currentPlatform },
  get os() { return currentOS },
  get isWeb() { return currentPlatform === PLATFORM_TYPES.WEB },
  get isMobile() { return currentPlatform === PLATFORM_TYPES.MOBILE },
  get isDesktop() { return false },
  get isTouch() { return isTouchDevice() },
  get apis() { return nativeApis || createFallbackApis() },
  PLATFORM_TYPES,
  OS_TYPES
}

export default platform
export { PLATFORM_TYPES, OS_TYPES }
