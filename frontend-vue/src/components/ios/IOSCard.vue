<template>
  <div class="ios-card" :class="{ 'ios-card-elevated': elevated, 'ios-card-pressable': pressable }">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  elevated: { type: Boolean, default: false },
  pressable: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
.ios-card {
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  box-shadow: var(--ios-shadow-sm);
  overflow: hidden;
  transition: all var(--ios-duration-normal) var(--ios-ease);
}

.ios-card-elevated {
  box-shadow: var(--ios-shadow-md);
}

.ios-card-pressable {
  cursor: pointer;

  @media (hover: hover) {
    &:hover {
      box-shadow: var(--ios-shadow-md);
      transform: translateY(-1px);
    }
  }

  &:active {
    transform: scale(0.98);
    box-shadow: var(--ios-shadow-sm);
  }
}
</style>
