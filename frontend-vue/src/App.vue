<template>
  <div id="app-root" class="app-root">
    <IOSNavBar title="MOM指数" />
    <main class="app-main ios-content-area">
      <router-view v-slot="{ Component }">
        <transition name="page-transition" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import IOSNavBar from '@/components/ios/IOSNavBar.vue'
import { useThemeStore } from '@/stores/theme'
import { useSystemStore } from '@/stores/system'
import platform from '@/platform/core'
import { initApi } from '@/core/api'

const themeStore = useThemeStore()
const systemStore = useSystemStore()

onMounted(async () => {
  // 必须 await：platform.init() 内部通过动态 import 加载原生 API，
  // 若不等待，platform.apis 会返回 fallback 空操作，导致窗口按钮失效
  await platform.init()

  systemStore.setPlatformInfo({
    platform: platform.type,
    os: platform.os,
    isDesktop: platform.isDesktop,
    isMobile: platform.isMobile,
    apis: platform.apis
  })

  // 初始化真实网络状态检测
  systemStore.initNetworkStatus()

  themeStore.initTheme()

  try {
    await initApi()
  } catch (e) {
    console.warn('API初始化警告:', e)
  }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.app-root {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--ios-bg-primary);
}

.app-main {
  flex: 1;
  min-height: 0;
  position: relative;
}

.page-transition-enter-active,
.page-transition-leave-active {
  transition: opacity var(--ios-duration-normal) var(--ios-ease),
              transform var(--ios-duration-normal) var(--ios-ease);
}

.page-transition-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-transition-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
