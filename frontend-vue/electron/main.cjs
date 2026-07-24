const { app, BrowserWindow, ipcMain, Menu, Tray, nativeImage, Notification, shell, dialog } = require('electron')
const path = require('path')
const fs = require('fs')
const http = require('http')
const net = require('net')

const isDev = !app.isPackaged
const isWindows = process.platform === 'win32'
const isMac = process.platform === 'darwin'
const isLinux = process.platform === 'linux'

let mainWindow = null
let tray = null
let backendProcess = null
let backendPort = 8000
let backendReady = false

const APP_CONFIG = {
  name: '宝妈指数',
  version: app.getVersion(),
  minWidth: 375,
  minHeight: 600,
  defaultWidth: 1280,
  defaultHeight: 800
}

function findAvailablePort(startPort) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.unref()
    server.on('error', () => findAvailablePort(startPort + 1).then(resolve))
    server.listen(startPort, () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
  })
}

async function checkBackendReady(port) {
  return new Promise((resolve) => {
    const timeout = setTimeout(() => resolve(false), 3000)
    const req = http.get(`http://localhost:${port}/api/system/health`, (res) => {
      clearTimeout(timeout)
      resolve(res.statusCode === 200)
    })
    req.on('error', () => {
      clearTimeout(timeout)
      resolve(false)
    })
  })
}

async function startBackend() {
  const rootDir = path.resolve(__dirname, '..', '..')
  const backendMain = path.join(rootDir, 'backend', 'main.py')

  if (fs.existsSync(backendMain)) {
    try {
      backendPort = await findAvailablePort(8000)
      const { spawn } = require('child_process')
      const pythonCommands = ['python', 'python3', 'py']
      let pythonCmd = null

      for (const cmd of pythonCommands) {
        try {
          const result = require('child_process').execSync(`${cmd} --version`, { stdio: 'pipe' })
          if (result.toString().includes('Python 3')) {
            pythonCmd = cmd
            break
          }
        } catch {}
      }

      if (pythonCmd) {
        backendProcess = spawn(pythonCmd, [backendMain], {
          cwd: rootDir,
          env: { ...process.env, PORT: backendPort.toString(), PYTHONUNBUFFERED: '1' },
          stdio: ['pipe', 'pipe', 'pipe']
        })

        backendProcess.stdout.on('data', (data) => {
          console.log(`[Backend] ${data}`)
        })
        backendProcess.stderr.on('data', (data) => {
          console.error(`[Backend Error] ${data}`)
        })
        backendProcess.on('close', (code) => {
          console.log(`[Backend] Process exited with code ${code}`)
          backendProcess = null
          backendReady = false
        })

        for (let i = 0; i < 30; i++) {
          await new Promise(r => setTimeout(r, 1000))
          if (await checkBackendReady(backendPort)) {
            backendReady = true
            console.log(`[Backend] Ready on port ${backendPort}`)
            break
          }
        }
      }
    } catch (e) {
      console.error('[Backend] Failed to start:', e)
    }
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: APP_CONFIG.defaultWidth,
    height: APP_CONFIG.defaultHeight,
    minWidth: APP_CONFIG.minWidth,
    minHeight: APP_CONFIG.minHeight,
    title: APP_CONFIG.name,
    backgroundColor: '#F2F2F7',
    icon: path.join(__dirname, '..', 'build', isWindows ? 'icon.ico' : isMac ? 'icon.icns' : 'icon.png'),
    titleBarStyle: isMac ? 'hiddenInset' : 'default',
    frame: !isWindows,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      nodeIntegration: false,
      contextIsolation: true,
      // 启用渲染进程沙箱：即使发生 Chromium 漏洞逃逸也限制其权限范围
      sandbox: true,
      webSecurity: true,
      devTools: isDev
    },
    show: false
  })

  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
    if (isDev) mainWindow.webContents.openDevTools()
  })

  if (isDev) {
    const devPort = process.env.VITE_DEV_PORT || 5174
    mainWindow.loadURL(`http://localhost:${devPort}`)
  } else {
    const indexPath = path.join(__dirname, '..', 'dist', 'index.html')
    mainWindow.loadFile(indexPath)
  }

  mainWindow.webContents.on('did-finish-load', () => {
    mainWindow.webContents.send('backend-port', { port: backendPort, ready: backendReady })
  })

  mainWindow.on('closed', () => { mainWindow = null })

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    // 仅允许 http/https 协议通过外部浏览器打开；file://、smb://、自定义协议等
    // 会被 shell.openExternal 交给系统处理，可能执行任意本地程序（CVE 常见模式）
    try {
      const parsed = new URL(url)
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        shell.openExternal(url)
      } else {
        console.warn(`[Security] 拒绝打开非 http(s) 协议链接: ${url}`)
      }
    } catch (e) {
      console.warn(`[Security] 无效 URL 被拒绝: ${url}`)
    }
    return { action: 'deny' }
  })
}

function createTray() {
  let iconPath = path.join(__dirname, '..', 'build', 'tray.png')
  if (!fs.existsSync(iconPath)) {
    iconPath = path.join(__dirname, '..', 'build', 'icon.png')
  }

  if (fs.existsSync(iconPath)) {
    const icon = nativeImage.createFromPath(iconPath)
    tray = new Tray(icon.resize({ width: 16, height: 16 }))

    const contextMenu = Menu.buildFromTemplate([
      { label: '显示主窗口', click: () => mainWindow && mainWindow.show() },
      { label: '刷新数据', click: () => mainWindow && mainWindow.webContents.send('refresh-data') },
      { type: 'separator' },
      { label: '退出', click: () => app.quit() }
    ])

    tray.setToolTip(APP_CONFIG.name)
    tray.setContextMenu(contextMenu)
    tray.on('double-click', () => {
      if (mainWindow) { mainWindow.show(); mainWindow.focus() }
    })
  }
}

function setupIPC() {
  ipcMain.handle('window-minimize', () => { mainWindow && mainWindow.minimize() })
  ipcMain.handle('window-maximize', () => {
    if (mainWindow) {
      if (mainWindow.isMaximized()) { mainWindow.unmaximize() } else { mainWindow.maximize() }
    }
  })
  ipcMain.handle('window-close', () => {
    if (isMac) { mainWindow && mainWindow.hide() } else { mainWindow && mainWindow.close() }
  })
  ipcMain.handle('window-is-maximized', () => mainWindow ? mainWindow.isMaximized() : false)
  ipcMain.handle('window-set-title', (_, title) => { mainWindow && mainWindow.setTitle(title || APP_CONFIG.name) })
  ipcMain.handle('window-set-always-on-top', (_, flag) => { mainWindow && mainWindow.setAlwaysOnTop(flag) })
  ipcMain.handle('app-get-version', () => APP_CONFIG.version)
  ipcMain.handle('app-get-system-info', () => ({
    platform: process.platform,
    arch: process.arch,
    version: process.getSystemVersion(),
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node
  }))
  ipcMain.handle('show-notification', (_, { title, body }) => {
    if (Notification.isSupported()) {
      const notification = new Notification({ title, body })
      notification.show()
      return true
    }
    return false
  })
  ipcMain.handle('open-external', (_, url) => {
    // open-external 同样需要协议白名单校验，防止渲染进程注入恶意协议
    try {
      const parsed = new URL(url)
      if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
        shell.openExternal(url)
      } else {
        console.warn(`[Security] open-external 拒绝非 http(s) 协议: ${url}`)
      }
    } catch (e) {
      console.warn(`[Security] open-external 无效 URL: ${url}`)
    }
  })
  ipcMain.handle('save-file', async (_, { defaultPath, data }) => {
    const result = await dialog.showSaveDialog(mainWindow, { defaultPath })
    if (result.filePath) {
      fs.writeFileSync(result.filePath, data, 'utf-8')
      return result.filePath
    }
    return null
  })
  ipcMain.handle('open-file', async (_, options = {}) => {
    const result = await dialog.showOpenDialog(mainWindow, options)
    if (!result.canceled && result.filePaths.length > 0) {
      const filePath = result.filePaths[0]
      const content = fs.readFileSync(filePath, 'utf-8')
      return { path: filePath, content }
    }
    return null
  })
  ipcMain.handle('get-backend-port', () => ({ port: backendPort, ready: backendReady }))
  ipcMain.handle('copy-to-clipboard', (_, text) => {
    const { clipboard } = require('electron')
    clipboard.writeText(text)
  })
  ipcMain.handle('read-from-clipboard', () => {
    const { clipboard } = require('electron')
    return clipboard.readText()
  })
}

app.whenReady().then(async () => {
  setupIPC()
  await startBackend()
  createWindow()
  createTray()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('window-all-closed', () => {
  if (!isMac) app.quit()
})

app.on('before-quit', () => {
  if (backendProcess) {
    try { backendProcess.kill() } catch {}
    backendProcess = null
  }
})

if (isMac) {
  app.on('dock-click', () => { if (mainWindow) mainWindow.show() })
}

if (!isDev) {
  Menu.setApplicationMenu(null)
}
