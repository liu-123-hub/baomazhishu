const api = window.electronAPI || {}

const electronApis = {
  available: !!window.electronAPI,

  async readFile(options) {
    if (api.openFile) return api.openFile(options)
    return new Promise((resolve) => {
      const input = document.createElement('input')
      input.type = 'file'
      input.accept = options?.accept || '.json,.txt,.csv'
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

  async writeFile(path, content) {
    if (api.saveFile) return api.saveFile(path, content)
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = path || 'export.txt'
    a.click()
    URL.revokeObjectURL(a.href)
    return true
  },

  async saveFile(content, filename) {
    return this.writeFile(filename, content)
  },

  async readFileDialog() {
    return this.readFile()
  },

  async showNotification(title, body) {
    if (api.showNotification) return api.showNotification(title, body)
    if ('Notification' in window) {
      if (Notification.permission === 'granted') { new Notification(title, { body }); return true }
      if (Notification.permission !== 'denied') {
        const perm = await Notification.requestPermission()
        if (perm === 'granted') { new Notification(title, { body }); return true }
      }
    }
    return false
  },

  async requestNotificationPermission() {
    if (api.requestNotificationPermission) return api.requestNotificationPermission()
    if ('Notification' in window) {
      const perm = await Notification.requestPermission()
      return perm === 'granted'
    }
    return false
  },

  setTitle(title) {
    if (api.setTitle) return api.setTitle(title)
    document.title = title
  },

  minimize() { return api.minimize?.() },
  maximize() { return api.maximize?.() },
  close() { return api.close?.() },
  isMaximized() { return api.isMaximized?.() || Promise.resolve(false) },

  async openExternal(url) {
    if (api.openExternal) return api.openExternal(url)
    window.open(url, '_blank')
  },
  async openUrl(url) { return this.openExternal(url) },

  async saveData(key, value) {
    if (api.saveData) return api.saveData(key, value)
    try { localStorage.setItem(`mom_${key}`, JSON.stringify(value)); return true } catch { return false }
  },
  async loadData(key, defaultValue = null) {
    if (api.loadData) return api.loadData(key, defaultValue)
    try {
      const data = localStorage.getItem(`mom_${key}`)
      return data ? JSON.parse(data) : defaultValue
    } catch { return defaultValue }
  },

  async getAppVersion() {
    if (api.getAppVersion) return api.getAppVersion()
    return '2.0.0-electron'
  },
  async getSystemInfo() {
    if (api.getSystemInfo) return api.getSystemInfo()
    return { platform: 'electron', os: navigator.platform }
  },

  async copyToClipboard(text) {
    if (api.copyToClipboard) return api.copyToClipboard(text)
    try { await navigator.clipboard.writeText(text); return true } catch { return false }
  },
  async readFromClipboard() {
    if (api.readFromClipboard) return api.readFromClipboard()
    try { return await navigator.clipboard.readText() } catch { return '' }
  },

  onRefreshData(callback) {
    if (api.onRefreshData) return api.onRefreshData(callback)
  },
  onBackendPort(callback) {
    if (api.onBackendPort) return api.onBackendPort(callback)
  },
  async getBackendPort() {
    if (api.getBackendPort) return api.getBackendPort()
    return { port: 8000, ready: false }
  },

  showDevTools() {
    if (window.__TAURI__ || window.electronAPI) return
  },
  reload() { location.reload() }
}

export default electronApis
