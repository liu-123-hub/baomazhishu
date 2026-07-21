/**
 * 手动打包脚本 - 构造win-unpacked目录
 * 由于网络限制无法下载electron-builder的额外二进制（NSIS等），
 * 使用本地node_modules/electron/dist直接构造可运行的桌面应用目录
 */
const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

const rootDir = path.resolve(__dirname, '..')
const electronDist = path.join(rootDir, 'node_modules', 'electron', 'dist')
const webDist = path.join(rootDir, 'dist')
const outDir = path.join(rootDir, 'release', 'electron', 'win-unpacked')
const backendDir = path.resolve(rootDir, '..', 'backend')

console.log('=== 手动构造 Electron 桌面应用 ===\n')

// 1. 检查electron dist
if (!fs.existsSync(path.join(electronDist, 'electron.exe'))) {
  console.error('错误: node_modules/electron/dist/electron.exe 不存在')
  console.error('请先运行: node node_modules/electron/install.js')
  process.exit(1)
}
console.log('[1/5] Electron 二进制: OK')

// 2. 检查web dist
if (!fs.existsSync(path.join(webDist, 'index.html'))) {
  console.error('错误: dist/index.html 不存在，请先运行 npm run electron:build:web')
  process.exit(1)
}
console.log('[2/5] Web 资源: OK')

// 3. 清空输出目录
if (fs.existsSync(outDir)) {
  console.log('[3/5] 清空旧输出目录...')
  fs.rmSync(outDir, { recursive: true, force: true })
}
fs.mkdirSync(outDir, { recursive: true })
console.log('[3/5] 输出目录已创建:', outDir)

// 4. 复制electron二进制
console.log('[4/5] 复制 Electron 运行时...')
copyDir(electronDist, outDir)

// 重命名electron.exe为应用名
const appExe = path.join(outDir, '宝妈指数.exe')
try {
  fs.renameSync(path.join(outDir, 'electron.exe'), appExe)
} catch (e) {
  // 如果中文名失败，用英文名
  fs.renameSync(path.join(outDir, 'electron.exe'), path.join(outDir, 'MomIndex.exe'))
}

// 5. 复制应用资源
console.log('[5/5] 复制应用资源...')

// 复制dist到resources/app
const appDir = path.join(outDir, 'resources', 'app')
fs.mkdirSync(appDir, { recursive: true })
copyDir(webDist, path.join(appDir, 'dist'))

// 复制electron主进程
const electronDir = path.join(appDir, 'electron')
fs.mkdirSync(electronDir, { recursive: true })
copyDir(path.join(rootDir, 'electron'), electronDir)

// 复制package.json
fs.copyFileSync(
  path.join(rootDir, 'package.json'),
  path.join(appDir, 'package.json')
)

// 复制backend（可选）
if (fs.existsSync(backendDir)) {
  console.log('  复制后端服务...')
  const backendTarget = path.join(outDir, 'resources', 'backend')
  copyDir(backendDir, backendTarget)
}

console.log('\n=== 打包完成 ===')
console.log('输出目录:', outDir)
console.log('\n可执行文件:')
const finalExe = fs.existsSync(appExe) ? appExe : path.join(outDir, 'MomIndex.exe')
console.log(' ', finalExe)
console.log('\n运行方式: 双击exe文件即可启动应用')

function copyDir(src, dest) {
  if (!fs.existsSync(src)) return
  const entries = fs.readdirSync(src, { withFileTypes: true })
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name)
    const destPath = path.join(dest, entry.name)
    if (entry.isDirectory()) {
      fs.mkdirSync(destPath, { recursive: true })
      copyDir(srcPath, destPath)
    } else {
      fs.copyFileSync(srcPath, destPath)
    }
  }
}
