<template>
  <div id="app-root" class="app-root">
    <IOSNavBar :title="navTitle" :showBack="showBack" :backLabel="'看板'" />
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
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import IOSNavBar from '@/components/ios/IOSNavBar.vue'
import { useThemeStore } from '@/stores/theme'
import { useSystemStore } from '@/stores/system'
import platform from '@/platform/core'
import { initApi } from '@/core/api'
import { SECTOR_NAMES } from '@/core/constants'

const route = useRoute()
const themeStore = useThemeStore()
const systemStore = useSystemStore()

const showBack = computed(() => route.meta?.showBack || false)
const navTitle = computed(() => {
  if (route.name === 'SectorDetail' && route.params.code) {
    const code = route.params.code
    return SECTOR_NAMES[code] || code
  }
  return route.meta?.title || 'MOM指数'
})

import { onMounted } from 'vue'
onMounted(async () => {
  await platform.init()

  systemStore.setPlatformInfo({
    platform: platform.type,
    os: platform.os,
    isDesktop: platform.isDesktop,
    isMobile: platform.isMobile,
    apis: platform.apis
  })

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
  transform: translateX(20px);
}

.page-transition-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}
</style>
