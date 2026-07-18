<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-brand" @click="goHome">
        <div class="brand-logo" aria-hidden="true">
          <svg viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="40" height="40" rx="10" fill="url(#logo-gradient)" />
            <path d="M10 26 L18 18 L22 22 L30 12" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
            <circle cx="30" cy="12" r="2.5" fill="white" />
            <defs>
              <linearGradient id="logo-gradient" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                <stop stop-color="#0ea5e9" />
                <stop offset="1" stop-color="#22c55e" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        <div class="brand-text">
          <span class="brand-title">MOM指数</span>
          <span class="brand-subtitle">股市情绪数据看板</span>
        </div>
      </div>

      <nav class="header-nav" aria-label="主导航">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          :class="['nav-link', { active: isActive(item) }]"
        >
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="header-actions">
        <DataUpdateStatus />
        <slot name="header-actions" />
      </div>
    </header>

    <main id="main-content" class="app-main">
      <slot />
    </main>

    <nav class="mobile-nav" aria-label="移动端导航">
      <router-link
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        :class="['mobile-nav-link', { active: isActive(item) }]"
      >
        <el-icon :size="22"><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </router-link>
    </nav>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DataLine } from '@element-plus/icons-vue'
import DataUpdateStatus from './DataUpdateStatus.vue'

const route = useRoute()
const router = useRouter()

const navItems = [
  { path: '/dashboard', label: '数据大屏', icon: DataLine }
]

const isActive = (item) => {
  return route.path === item.path || route.path.startsWith(item.path + '/')
}

function goHome() {
  router.push('/')
}
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  min-height: 100dvh;
}

.app-header {
  @include flex-between;
  position: sticky;
  top: 0;
  z-index: $z-index-sticky-header;
  height: 64px;
  padding: 0 $spacing-6;
  @include glass-effect(12px, rgba(15, 23, 42, 0.8), #0f172a);
  border-bottom: 1px solid $color-border;
  flex-shrink: 0;
  // 提升为独立合成层，降低滚动时与内容的交叉重绘；同时限制绘制范围
  transform: translateZ(0);
  backface-visibility: hidden;
  contain: layout paint;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: $spacing-3;
  cursor: pointer;

  .brand-logo {
    width: 36px;
    height: 36px;
    flex-shrink: 0;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .brand-text {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }

  .brand-title {
    font-size: $font-size-lg;
    font-weight: $font-weight-bold;
    color: $color-text-primary;
    letter-spacing: -0.02em;
  }

  .brand-subtitle {
    font-size: $font-size-xs;
    color: $color-text-tertiary;
  }
}

.header-nav {
  display: flex;
  align-items: center;
  gap: $spacing-1;

  .nav-link {
    display: flex;
    align-items: center;
    gap: $spacing-2;
    padding: $spacing-2 $spacing-4;
    border-radius: $radius-md;
    color: $color-text-secondary;
    font-size: $font-size-sm;
    font-weight: $font-weight-medium;
    text-decoration: none;
    // 仅过渡颜色与背景色，避免 all 造成的额外合成开销
    transition: color $transition-fast, background-color $transition-fast;

    &:hover {
      color: $color-text-primary;
      background: $color-bg-hover;
    }

    &.active {
      color: $color-primary;
      background: $color-primary-100;
    }

    .el-icon {
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: $spacing-3;
}

.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.mobile-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: $z-index-fixed;
  height: 60px;
  padding-bottom: env(safe-area-inset-bottom, 0px);
  @include glass-effect(16px, rgba(15, 23, 42, 0.9), #0f172a);
  border-top: 1px solid $color-border;
}

.mobile-nav-link {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: $color-text-tertiary;
  font-size: 11px;
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: $color-text-secondary;
  }

  &.active {
    color: $color-primary;
  }
}

@media (max-width: $breakpoint-md) {
  .app-header {
    height: 56px;
    padding: 0 $spacing-4;
    // 移动端降低模糊半径，减少 GPU 开销
    @include glass-effect(8px, rgba(15, 23, 42, 0.9), #0f172a);
  }

  .header-nav,
  .header-actions {
    display: none;
  }

  .brand-subtitle {
    display: none;
  }

  .app-main {
    padding-bottom: 60px;
  }

  .mobile-nav {
    display: flex;
    // 固定底部导航同样提升为独立合成层
    transform: translateZ(0);
    backface-visibility: hidden;
    contain: layout paint;
  }
}
</style>
