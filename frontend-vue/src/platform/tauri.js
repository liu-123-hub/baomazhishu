/**
 * Tauri 原生API实现
 */

let tauriModules = null

const _dynImport = (p) => import(/* @vite-ignore */ p)

async function loadTauriModules() {
  if (tauriModules) return tauriModules
  
  try {
    const [
      { invoke },
      { listen },
      { getCurrentWindow },
      { writeText, readText },
      { open },
      { save, open: openDialog }
    ] = await Promise.all([
      _dynImport('@tauri-apps/api/core'),
      _dynImport('@tauri-apps/api/event'),
      _dynImport('@tauri-apps/api/window'),
      _dynImport('@tauri-apps/plugin-clipboard-manager'),
      _dynImport('@tauri-apps/plugin-shell'),
      _dynImport('@tauri-apps/plugin-dialog')
    ])
    
    let notificationModule = null
    try {
      notificationModule = (await _dynImport('@tauri-apps/plugin-notification'))
    } catch {
      // notification plugin optional
    }
    
    let fsModule = null
    try {
      fsModule = (await _dynImport('@tauri-apps/plugin-fs'))
    } catch {
      // fs plugin optional
    }
    
    tauriModules = {
      invoke, listen,
      getCurrentWindow,
      writeText, readText,
      open, openDialog, save,
      notification: notificationModule || null,
      fs: fsModule || null
    }
    
    return tauriModules
  } catch (e) {
    console.error('[Tauri] Failed to load Tauri modules:', e)
    throw e
  }
}

const tauriApi = {
  async readFile(path) {
    const mods = await loadTauriModules()
    if (mods.fs) {
      return await mods.fs.readTextFile(path)
    }
    return await mods.invoke('read_file', { path })
  },
  
  async writeFile(path, data) {
    const mods = await loadTauriModules()
    if (mods.fs) {
      await mods.fs.writeTextFile(path, data)
      return true
    }
    return await mods.invoke('write_file', { path, data })
  },
  
  async showNotification(title, body) {
    const mods = await loadTauriModules()
    if (mods.notification && mods.notification.isPermissionGranted()) {
      await mods.notification.sendNotification({ title, body })
      return true
    } else if (mods.notification) {
      const permission = await mods.notification.requestPermission()
      if (permission === 'granted') {
        await mods.notification.sendNotification({ title, body })
        return true
      }
    }
    return false
  },
  
  async requestNotificationPermission() {
    const mods = await loadTauriModules()
    if (mods.notification) {
      const permission = await mods.notification.requestPermission()
      return permission === 'granted'
    }
    return false
  },
  
  async setTitle(title) {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    await win.setTitle(title)
  },
  
  async minimize() {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    await win.minimize()
  },
  
  async maximize() {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    const maximized = await win.isMaximized()
    if (maximized) {
      await win.unmaximize()
    } else {
      await win.maximize()
    }
  },
  
  async close() {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    await win.close()
  },
  
  async isMaximized() {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    return await win.isMaximized()
  },
  
  async openExternal(url) {
    const mods = await loadTauriModules()
    await mods.open(url)
  },
  
  async openUrl(url) {
    return this.openExternal(url)
  },
  
  async saveData(key, value) {
    try {
      localStorage.setItem(`mom_${key}`, JSON.stringify(value))
      return true
    } catch {
      return false
    }
  },
  
  async loadData(key, defaultValue = null) {
    try {
      const data = localStorage.getItem(`mom_${key}`)
      return data ? JSON.parse(data) : defaultValue
    } catch {
      return defaultValue
    }
  },
  
  async saveFile(content, filename) {
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = filename
    a.click()
    URL.revokeObjectURL(a.href)
  },
  
  async setAlwaysOnTop(alwaysOnTop) {
    const mods = await loadTauriModules()
    const win = mods.getCurrentWindow()
    await win.setAlwaysOnTop(alwaysOnTop)
  },
  
  async copyToClipboard(text) {
    const mods = await loadTauriModules()
    await mods.writeText(text)
  },
  
  async readFromClipboard() {
    const mods = await loadTauriModules()
    return await mods.readText()
  },
  
  async getAppVersion() {
    const mods = await loadTauriModules()
    try {
      return await mods.invoke('get_app_version')
    } catch {
      return '2.0.0-tauri'
    }
  },
  
  async getSystemInfo() {
    const mods = await loadTauriModules()
    try {
      return await mods.invoke('get_system_info')
    } catch {
      return { platform: 'tauri', version: navigator.userAgent }
    }
  },
  
  showDevTools() {
    console.log('[Tauri] dev tools controlled by Tauri')
  },
  
  reload() { location.reload() }
}

export default tauriApi
