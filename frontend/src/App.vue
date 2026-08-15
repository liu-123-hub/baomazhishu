<template>
  <div id="app-root" class="app-root" :class="{ 'theme-dark': themeStore.isDark }">
    <a href="#main-content" class="skip-link">跳转到主要内容</a>
    <IOSNavBar :title="navTitle" :showBack="showBack" :backLabel="'看板'" />
    <main id="main-content" class="app-main ios-content-area" role="main" tabindex="-1">
      <router-view v-slot="{ Component }">
        <transition name="page-transition" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
    <IOSToast
      v-model="toastStore.visible"
      :message="toastStore.message"
      :type="toastStore.type"
      :duration="toastStore.duration"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import IOSNavBar from '@/components/ios/IOSNavBar.vue'
import IOSToast from '@/components/ios/IOSToast.vue'
import { useThemeStore } from '@/stores/theme'
import { useSystemStore } from '@/stores/system'
import { useToastStore } from '@/stores/toast'
import platform from '@/platform/core'
import { initApi } from '@/core/api'
import { SECTOR_NAMES, APP_CONFIG } from '@/core/constants'

const route = useRoute()
const themeStore = useThemeStore()
const systemStore = useSystemStore()
const toastStore = useToastStore()

const showBack = computed(() => route.meta?.showBack || false)
const navTitle = computed(() => {
  if (route.name === 'SectorDetail' && route.params.code) {
    const code = route.params.code
    return SECTOR_NAMES[code] || code
  }
  return route.meta?.title || APP_CONFIG.name
})


function handleUnhandledRejection(event) {
  console.error('[UnhandledRejection]', event.reason)
  const error = event.reason
  if (error?.userMessage) {
    toastStore.error(error.userMessage)
  }
}


function handleGlobalError(event) {
  console.error('[GlobalError]', event.error || event.message)
}


let isKeyboardUser = false

function handleKeyDown(e) {
  if (e.key === 'Tab' || (e.key.startsWith('Arrow'))) {
    isKeyboardUser = true
    document.documentElement.classList.add('user-is-keyboard')
    document.documentElement.classList.remove('user-is-pointer')
  }
}

function handlePointerDown() {
  isKeyboardUser = false
  document.documentElement.classList.remove('user-is-keyboard')
  document.documentElement.classList.add('user-is-pointer')

  
  const active = document.activeElement
  if (
    active &&
    active !== document.body &&
    !['INPUT', 'TEXTAREA', 'SELECT', 'CONTENTEDITABLE'].includes(active.tagName) &&
    !active.isContentEditable
  ) {
    
    setTimeout(() => {
      if (document.activeElement === active && !isKeyboardUser) {
        active.blur()
      }
    }, 0)
  }
}


function handleDocumentClick(e) {
  if (isKeyboardUser) return
  const target = e.target
  
  const isInteractive = target.closest(
    'button, a, input, textarea, select, [role="button"], [tabindex]:not([tabindex="-1"])'
  )
  if (!isInteractive) {
    const active = document.activeElement
    if (
      active &&
      active !== document.body &&
      !['INPUT', 'TEXTAREA', 'SELECT'].includes(active.tagName) &&
      !active.isContentEditable
    ) {
      active.blur()
    }
  }
}

onMounted(async () => {
  
  window.addEventListener('unhandledrejection', handleUnhandledRejection)
  window.addEventListener('error', handleGlobalError)

  
  window.addEventListener('keydown', handleKeyDown, true)
  window.addEventListener('mousedown', handlePointerDown, true)
  window.addEventListener('touchstart', handlePointerDown, { passive: true, capture: true })
  document.addEventListener('click', handleDocumentClick, true)

  
  document.documentElement.classList.add('user-is-pointer')

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
    toastStore.warning('API服务初始化异常，部分功能可能不可用')
  }
})

onUnmounted(() => {
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  window.removeEventListener('error', handleGlobalError)
  window.removeEventListener('keydown', handleKeyDown, true)
  window.removeEventListener('mousedown', handlePointerDown, true)
  window.removeEventListener('touchstart', handlePointerDown, true)
  document.removeEventListener('click', handleDocumentClick, true)
  document.documentElement.classList.remove('user-is-keyboard', 'user-is-pointer')
  
  systemStore.cleanupNetworkStatus()
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
  color: var(--ios-label-primary);
}

.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--ios-blue);
  color: white;
  padding: 8px 16px;
  z-index: 10000;
  border-radius: 0 0 var(--ios-radius-md) 0;
  font-size: var(--ios-text-sm);
  font-weight: 500;
  transition: top var(--ios-duration-fast) var(--ios-ease);

  &:focus {
    top: 0;
  }
}

.app-main {
  flex: 1;
  min-height: 0;
  position: relative;
  outline: none;
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

@media (prefers-reduced-motion: reduce) {
  .page-transition-enter-active,
  .page-transition-leave-active {
    transition: opacity var(--ios-duration-fast) var(--ios-ease);
  }

  .page-transition-enter-from,
  .page-transition-leave-to {
    transform: none;
  }
}
</style>
