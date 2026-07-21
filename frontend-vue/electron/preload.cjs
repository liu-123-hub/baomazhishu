const { contextBridge, ipcRenderer } = require('electron')

const electronAPI = {
  platform: 'electron',

  minimize: () => ipcRenderer.invoke('window-minimize'),
  maximize: () => ipcRenderer.invoke('window-maximize'),
  close: () => ipcRenderer.invoke('window-close'),
  isMaximized: () => ipcRenderer.invoke('window-is-maximized'),
  setTitle: (title) => ipcRenderer.invoke('window-set-title', title),
  setAlwaysOnTop: (flag) => ipcRenderer.invoke('window-set-always-on-top', flag),

  getAppVersion: () => ipcRenderer.invoke('app-get-version'),
  getSystemInfo: () => ipcRenderer.invoke('app-get-system-info'),

  showNotification: (title, body) => ipcRenderer.invoke('show-notification', { title, body }),
  requestNotificationPermission: async () => true,

  openExternal: (url) => ipcRenderer.invoke('open-external', url),

  saveData: async (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)); return true } catch { return false }
  },
  loadData: async (key) => {
    try {
      const data = localStorage.getItem(key)
      return data ? JSON.parse(data) : null
    } catch { return null }
  },

  saveFile: (defaultPath, data) => ipcRenderer.invoke('save-file', { defaultPath, data }),
  openFile: (options) => ipcRenderer.invoke('open-file', options),

  copyToClipboard: (text) => ipcRenderer.invoke('copy-to-clipboard', text),
  readFromClipboard: () => ipcRenderer.invoke('read-from-clipboard'),

  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),

  onRefreshData: (callback) => { ipcRenderer.on('refresh-data', callback) },
  onBackendPort: (callback) => { ipcRenderer.on('backend-port', (event, data) => callback(data)) }
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)
