<template>
  <nav class="ios-nav-bar" :class="{ 'nav-dark': themeStore.isDark }">
    <div class="nav-left">
      <button v-if="showBack" class="nav-back ios-touch-target" @click="goBack">
        <svg width="12" height="20" viewBox="0 0 12 20" fill="none">
          <path d="M10 2L2 10L10 18" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <span class="back-label">{{ backLabel }}</span>
      </button>
      <div v-if="systemStore.isDesktop && systemStore.os === 'macos'" class="window-controls">
        <button class="ios-window-btn ios-window-btn-close" @click="handleClose" title="关闭"></button>
        <button class="ios-window-btn ios-window-btn-minimize" @click="handleMinimize" title="最小化"></button>
        <button class="ios-window-btn ios-window-btn-maximize" @click="handleMaximize" title="最大化"></button>
      </div>
      <div class="nav-title" :class="{ 'nav-title-with-back': showBack }">
        <span class="title-text">{{ title }}</span>
      </div>
    </div>
    <div class="nav-right">
      <button class="theme-toggle ios-touch-target" @click="toggleTheme" :title="themeStore.isDark ? '切换到浅色模式' : '切换到深色模式'">
        <span class="theme-icon">{{ themeStore.isDark ? '☀️' : '🌙' }}</span>
      </button>
      <div v-if="systemStore.isDesktop && systemStore.os === 'windows'" class="window-controls windows-controls">
        <button class="win-btn" @click="handleMinimize" title="最小化">
          <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0" y="4.5" width="10" height="1" fill="currentColor"/></svg>
        </button>
        <button class="win-btn" @click="handleMaximize" title="最大化">
          <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9" fill="none" stroke="currentColor" stroke-width="1"/></svg>
        </button>
        <button class="win-btn win-close" @click="handleClose" title="关闭">
          <svg width="10" height="10" viewBox="0 0 10 10"><line x1="0" y1="0" x2="10" y2="10" stroke="currentColor" stroke-width="1"/><line x1="10" y1="0" x2="0" y2="10" stroke="currentColor" stroke-width="1"/></svg>
        </button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
import { useSystemStore } from '@/stores/system'

const props = defineProps({
  title: {
    type: String,
    default: 'MOM指数'
  },
  showBack: {
    type: Boolean,
    default: false
  },
  backLabel: {
    type: String,
    default: '返回'
  }
})

const router = useRouter()
const themeStore = useThemeStore()
const systemStore = useSystemStore()

function toggleTheme() {
  themeStore.toggleTheme()
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
  } else {
    router.push('/dashboard')
  }
}

function handleMinimize() {
  systemStore.minimizeWindow()
}

function handleMaximize() {
  systemStore.maximizeWindow()
}

function handleClose() {
  systemStore.closeWindow()
}
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-nav-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: calc(var(--ios-nav-height) + env(safe-area-inset-top, 0px));
  padding: env(safe-area-inset-top, 0px) var(--ios-spacing-lg) 0;
  user-select: none;
  -webkit-user-select: none;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--ios-separator);

  &.nav-dark {
    background: rgba(28, 28, 30, 0.85);
  }

  @include mobile {
    padding-left: var(--ios-spacing-md);
    padding-right: var(--ios-spacing-md);
  }
}

.nav-left {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  min-width: 0;
  flex: 1;

  @include mobile {
    gap: var(--ios-spacing-xs);
  }
}

.nav-back {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: var(--ios-spacing-xs) var(--ios-spacing-sm);
  margin-left: calc(var(--ios-spacing-xs) * -1);
  border: none;
  background: none;
  color: var(--ios-blue);
  font-size: var(--ios-text-base);
  cursor: pointer;
  border-radius: var(--ios-radius-md);
  transition: all var(--ios-duration-fast) var(--ios-ease);
  flex-shrink: 0;

  svg {
    flex-shrink: 0;
  }

  .back-label {
    font-size: var(--ios-text-base);
    @include mobile {
      display: none;
    }
  }

  &:active {
    opacity: 0.5;
  }
}

.nav-title {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 0;

  &.nav-title-with-back {
    margin-right: 60px;
  }
}

.title-text {
  font-size: var(--ios-text-lg);
  font-weight: 600;
  color: var(--ios-label-primary);
  letter-spacing: -0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-right {
  display: flex;
  align-items: center;
  gap: var(--ios-spacing-sm);
  flex-shrink: 0;
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--ios-radius-full);
  background: var(--ios-fill-primary);
  transition: all var(--ios-duration-fast) var(--ios-ease);
  font-size: 18px;

  @media (hover: hover) {
    &:hover {
      background: var(--ios-fill-secondary);
    }
  }

  &:active {
    transform: scale(0.92);
    background: var(--ios-fill-tertiary);
  }
}

.theme-icon {
  line-height: 1;
}

.window-controls {
  display: flex;
  gap: var(--ios-spacing-sm);
}

.windows-controls {
  gap: 0;
  margin-left: var(--ios-spacing-sm);
}

.win-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 32px;
  color: var(--ios-label-secondary);
  transition: background var(--ios-duration-fast) var(--ios-ease);

  @media (hover: hover) {
    &:hover {
      background: var(--ios-fill-primary);
      color: var(--ios-label-primary);
    }
  }

  &:active {
    background: var(--ios-fill-secondary);
  }

  &.win-close {
    @media (hover: hover) {
      &:hover {
        background: var(--ios-red);
        color: white;
      }
    }
  }
}
</style>
