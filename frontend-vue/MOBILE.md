# 移动端 (iOS/Android) 打包说明

## 环境要求

### Android
- Android Studio (https://developer.android.com/studio)
- Android SDK (API 33+)
- Java JDK 17

### iOS (仅 macOS)
- Xcode 14+
- CocoaPods
- Apple Developer 账号 (用于发布)

## 打包流程

### 1. 构建移动端Web资源
```bash
cd frontend-vue
npm run build:mobile    # 输出到 dist-mobile/
```

### 2. 添加原生平台 (首次)
```bash
# Android
npx cap add android

# iOS (仅macOS)
npx cap add ios
```

### 3. 同步Web资源到原生项目
```bash
npx cap sync
# 或分别同步
npx cap sync android
npx cap sync ios
```

### 4. 打开原生IDE进行打包

#### Android (Android Studio)
```bash
npx cap open android
# 在Android Studio中:
# Build > Generate Signed Bundle / APK
# 选择 APK 或 Android App Bundle
# 配置签名 keystore
# 选择 release 构建类型
```

#### iOS (Xcode)
```bash
npx cap open ios
# 在Xcode中:
# Product > Archive
# Distribute App
```

### 5. 一键构建命令
```bash
# Android
npm run cap:build:android

# iOS
npm run cap:build:ios
```

## 打包产物

| 平台 | 产物格式 | 路径 |
|------|---------|------|
| Android | `.apk` | `android/app/build/outputs/apk/release/` |
| Android | `.aab` | `android/app/build/outputs/bundle/release/` |
| iOS | `.ipa` | Xcode Archive 导出 |

## PWA 部署 (无需原生打包)

```bash
npm run build:pwa    # 输出到 dist/ (含Service Worker)
```

部署 `dist/` 目录到任意静态服务器，用户通过浏览器访问即可"安装到桌面"。

## Capacitor 插件配置

项目已配置以下Capacitor插件（在 `src/platform/capacitor.js` 中使用）：

| 插件 | 功能 |
|------|------|
| @capacitor/app | 应用生命周期管理 |
| @capacitor/device | 设备信息 |
| @capacitor/local-notifications | 本地通知 |
| @capacitor/filesystem | 文件系统读写 |
| @capacitor/preferences | 键值存储 |
| @capacitor/browser | 内置浏览器 |
| @capacitor/haptics | 触觉反馈 |
| @capacitor/status-bar | 状态栏控制 |
| @capacitor/share | 系统分享 |

安装插件:
```bash
npm install @capacitor/app @capacitor/device @capacitor/local-notifications @capacitor/filesystem @capacitor/preferences @capacitor/browser @capacitor/haptics @capacitor/status-bar @capacitor/share
npx cap sync
```

## 移动端适配

- ✅ 响应式布局 (mobile/tablet/desktop断点)
- ✅ Safe Area 适配 (刘海屏/底部安全区)
- ✅ 触摸优化 (tap-highlight, touch-target)
- ✅ 深色模式支持
- ✅ PWA 离线运行
- ✅ 原生通知
- ✅ 触觉反馈
- ✅ 状态栏控制
