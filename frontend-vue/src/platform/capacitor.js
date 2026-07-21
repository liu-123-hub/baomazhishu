/**
 * Capacitor (移动端) 原生API实现
 */

let capacitorModules = null

const _dynImport = (p) => import(/* @vite-ignore */ p)

async function loadCapacitorModules() {
  if (capacitorModules) return capacitorModules
  
  try {
    const [
      { App },
      { Device },
      { LocalNotifications },
      { Filesystem, Directory },
      { Preferences },
      { Browser },
      { Haptics, ImpactStyle },
      { StatusBar, Style: StatusBarStyle }
    ] = await Promise.all([
      _dynImport('@capacitor/app'),
      _dynImport('@capacitor/device'),
      _dynImport('@capacitor/local-notifications'),
      _dynImport('@capacitor/filesystem'),
      _dynImport('@capacitor/preferences'),
      _dynImport('@capacitor/browser'),
      _dynImport('@capacitor/haptics'),
      _dynImport('@capacitor/status-bar')
    ])
    
    capacitorModules = {
      App, Device, LocalNotifications,
      Filesystem, Directory, Preferences,
      Browser, Haptics, ImpactStyle,
      StatusBar, StatusBarStyle
    }
    
    return capacitorModules
  } catch (e) {
    console.error('[Capacitor] Failed to load Capacitor modules:', e)
    throw e
  }
}

const capacitorApi = {
  async readFile(path) {
    const mods = await loadCapacitorModules()
    try {
      const result = await mods.Filesystem.readFile({
        path,
        directory: mods.Directory.Documents
      })
      return result.data
    } catch {
      return null
    }
  },
  
  async writeFile(path, data) {
    const mods = await loadCapacitorModules()
    try {
      await mods.Filesystem.writeFile({
        path,
        data,
        directory: mods.Directory.Documents,
        recursive: true
      })
      return true
    } catch {
      return false
    }
  },
  
  async showNotification(title, body) {
    try {
      const mods = await loadCapacitorModules()
      await mods.LocalNotifications.schedule({
        notifications: [{
          id: Date.now(),
          title,
          body,
          schedule: { at: new Date(Date.now() + 100) }
        }]
      })
      return true
    } catch {
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, { body })
        return true
      }
      return false
    }
  },
  
  async requestNotificationPermission() {
    try {
      const mods = await loadCapacitorModules()
      const perm = await mods.LocalNotifications.requestPermissions()
      return perm.display === 'granted'
    } catch {
      if ('Notification' in window) {
        const perm = await Notification.requestPermission()
        return perm === 'granted'
      }
      return false
    }
  },
  
  async setTitle(title) {
    document.title = title
    try {
      const mods = await loadCapacitorModules()
      await mods.StatusBar.setStyle({ style: 'DARK' })
    } catch {}
  },
  
  async minimize() {
    try {
      const mods = await loadCapacitorModules()
      await mods.App.minimizeApp()
    } catch {}
  },
  
  async maximize() {},
  
  async close() {
    try {
      const mods = await loadCapacitorModules()
      await mods.App.exitApp()
    } catch {}
  },
  
  async isMaximized() { return true },
  
  async openExternal(url) {
    try {
      const mods = await loadCapacitorModules()
      await mods.Browser.open({ url })
    } catch {
      window.open(url, '_blank')
    }
  },
  
  async openUrl(url) {
    return this.openExternal(url)
  },
  
  async saveData(key, value) {
    try {
      const mods = await loadCapacitorModules()
      await mods.Preferences.set({ key, value: JSON.stringify(value) })
      return true
    } catch {
      try {
        localStorage.setItem(`mom_${key}`, JSON.stringify(value))
        return true
      } catch { return false }
    }
  },
  
  async loadData(key, defaultValue = null) {
    try {
      const mods = await loadCapacitorModules()
      const result = await mods.Preferences.get({ key })
      return result.value ? JSON.parse(result.value) : defaultValue
    } catch {
      try {
        const data = localStorage.getItem(`mom_${key}`)
        return data ? JSON.parse(data) : defaultValue
      } catch { return defaultValue }
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
  
  async hapticFeedback(style = 'medium') {
    try {
      const mods = await loadCapacitorModules()
      const impactStyle = style === 'light' ? mods.ImpactStyle.Light :
                         style === 'heavy' ? mods.ImpactStyle.Heavy :
                         mods.ImpactStyle.Medium
      await mods.Haptics.impact({ style: impactStyle })
    } catch {}
  },
  
  async setStatusBarColor(color, isDark = false) {
    try {
      const mods = await loadCapacitorModules()
      await mods.StatusBar.setBackgroundColor({ color })
      await mods.StatusBar.setStyle({ style: isDark ? 'DARK' : 'LIGHT' })
    } catch {}
  },
  
  async getAppVersion() {
    try {
      const mods = await loadCapacitorModules()
      const info = await mods.App.getInfo()
      return info.version
    } catch {
      return '2.0.0-mobile'
    }
  },
  
  async getSystemInfo() {
    try {
      const mods = await loadCapacitorModules()
      const deviceInfo = await mods.Device.getInfo()
      return {
        platform: 'capacitor',
        os: deviceInfo.operatingSystem,
        osVersion: deviceInfo.osVersion,
        model: deviceInfo.model,
        manufacturer: deviceInfo.manufacturer
      }
    } catch {
      return { platform: 'mobile', userAgent: navigator.userAgent }
    }
  },
  
  async share(data) {
    try {
      const { Share } = await _dynImport('@capacitor/share')
      await Share.share(data)
      return true
    } catch {
      if (navigator.share) {
        try { await navigator.share(data); return true } catch {}
      }
      return false
    }
  },
  
  showDevTools() {},
  reload() { location.reload() }
}

export default capacitorApi
