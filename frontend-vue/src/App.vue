<template>
  <AppLayout>
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </AppLayout>
</template>

<script setup>
import AppLayout from '@/components/AppLayout.vue'
</script>

<style lang="scss" scoped>
.app-layout :deep(.app-main) > * {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
</style>
