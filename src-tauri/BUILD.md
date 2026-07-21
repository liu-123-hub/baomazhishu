# Tauri 桌面应用打包说明

## 环境要求

Tauri 打包需要以下环境（与 Electron 不同，Tauri 使用 Rust 作为后端）：

### 1. Rust 工具链
```powershell
# Windows (PowerShell)
Invoke-WebRequest https://win.rustup.rs/x86_64 -OutFile rustup-init.exe
.\rustup-init.exe -y

# macOS
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Linux
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 2. 系统依赖

#### Windows
- Microsoft Visual Studio C++ Build Tools
  - 安装 "Desktop development with C++" 工作负载
  - 下载: https://visualstudio.microsoft.com/visual-cpp-build-tools/
- WebView2 (Windows 10/11 通常已预装)

#### macOS
- Xcode Command Line Tools: `xcode-select --install`

#### Linux (Debian/Ubuntu)
```bash
sudo apt update
sudo apt install -y libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev
```

## 打包命令

在 `frontend-vue` 目录下执行：

```bash
# 开发模式（热重载）
npm run dev:tauri

# 打包当前平台安装包
npm run build:tauri

# 或直接使用 tauri CLI
npx tauri build
```

## 打包产物

打包产物位于 `src-tauri/target/release/bundle/`：

| 平台 | 产物格式 | 路径 |
|------|---------|------|
| Windows | `.msi` (NSIS安装包) | `bundle/msi/` |
| Windows | `.exe` (NSIS安装包) | `bundle/nsis/` |
| macOS | `.dmg` (磁盘映像) | `bundle/dmg/` |
| macOS | `.app` (应用包) | `bundle/macos/` |
| Linux | `.deb` (Debian包) | `bundle/deb/` |
| Linux | `.AppImage` (便携版) | `bundle/appimage/` |
| Linux | `.rpm` (RedHat包) | `bundle/rpm/` |

## 跨平台打包

Tauri 支持交叉编译（需要额外配置）：

```bash
# 仅 Windows
npx tauri build --target x86_64-pc-windows-msvc

# 仅 macOS (Intel)
npx tauri build --target x86_64-apple-darwin

# 仅 macOS (Apple Silicon)
npx tauri build --target aarch64-apple-darwin

# 仅 Linux
npx tauri build --target x86_64-unknown-linux-gnu
```

## Tauri vs Electron 对比

| 特性 | Tauri | Electron |
|------|-------|----------|
| 后端语言 | Rust | Node.js |
| 安装包大小 | ~10MB | ~170MB |
| 内存占用 | 低 | 较高 |
| 系统WebView | 使用系统WebView | 内置Chromium |
| 启动速度 | 快 | 较慢 |
| 安全性 | 高（沙箱隔离） | 中 |
| 原生API | 通过Rust插件 | 通过Node.js |

## 当前项目配置

- **应用名**: 宝妈指数
- **应用ID**: com.momindex.app
- **版本**: 2.0.0
- **最小窗口**: 375×600 (支持移动端布局)
- **默认窗口**: 1280×800
- **Tauri插件**: shell, dialog, fs, notification, clipboard-manager
- **Rust最低版本**: 1.77
- **macOS最低版本**: 12.0

## 验证清单

- [ ] Rust 工具链已安装 (`rustc --version`)
- [ ] Cargo 已安装 (`cargo --version`)
- [ ] 系统依赖已安装
- [ ] `npm run dev:tauri` 开发模式可正常启动
- [ ] `npm run build:tauri` 可生成安装包
- [ ] 安装包可在目标系统正常安装运行
- [ ] 窗口管理（最小化/最大化/关闭）正常
- [ ] 系统通知功能正常
- [ ] 文件读写功能正常
- [ ] 剪贴板功能正常
