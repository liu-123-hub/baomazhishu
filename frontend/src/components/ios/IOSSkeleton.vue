<template>
  <div class="ios-skeleton-card" :class="{ 'pulse': animated }">
    <div v-if="variant === 'card'" class="skeleton-card">
      <div class="skeleton-header">
        <div class="skeleton-icon skeleton-block"></div>
        <div class="skeleton-title skeleton-block"></div>
      </div>
      <div class="skeleton-value skeleton-block"></div>
      <div class="skeleton-sub skeleton-block"></div>
    </div>

    <div v-else-if="variant === 'chart'" class="skeleton-chart">
      <div class="skeleton-chart-header">
        <div class="skeleton-block" style="width: 80px; height: 20px;"></div>
      </div>
      <div class="skeleton-chart-area skeleton-block"></div>
      <div class="skeleton-chart-legend">
        <div v-for="i in 4" :key="i" class="skeleton-legend-item skeleton-block"></div>
      </div>
    </div>

    <div v-else-if="variant === 'list'" class="skeleton-list">
      <div v-for="i in rows" :key="i" class="skeleton-list-item">
        <div class="skeleton-dot skeleton-block"></div>
        <div class="skeleton-list-text skeleton-block"></div>
        <div class="skeleton-list-value skeleton-block"></div>
      </div>
    </div>

    <div v-else class="skeleton-generic">
      <div v-for="i in lines" :key="i" class="skeleton-line skeleton-block" :style="{ width: `${100 - (i * 15) % 40}%` }"></div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  variant: { type: String, default: 'card', validator: v => ['card', 'chart', 'list', 'text'].includes(v) },
  rows: { type: Number, default: 5 },
  lines: { type: Number, default: 3 },
  animated: { type: Boolean, default: true }
})
</script>

<style lang="scss" scoped>
@use '@/styles/variables.scss' as *;

.ios-skeleton-card {
  background: var(--ios-bg-secondary);
  border-radius: var(--ios-radius-lg);
  padding: var(--ios-spacing-lg);
}

.skeleton-block {
  background: linear-gradient(
    90deg,
    var(--ios-fill-primary) 25%,
    var(--ios-fill-secondary) 50%,
    var(--ios-fill-primary) 75%
  );
  background-size: 200% 100%;
  border-radius: var(--ios-radius-sm);
}

.pulse .skeleton-block {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
  will-change: opacity;
}

@keyframes skeleton-pulse {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}


.skeleton-card {
  .skeleton-header {
    display: flex;
    align-items: center;
    gap: var(--ios-spacing-sm);
    margin-bottom: var(--ios-spacing-md);
  }

  .skeleton-icon {
    width: 32px;
    height: 32px;
    border-radius: var(--ios-radius-md);
  }

  .skeleton-title {
    width: 100px;
    height: 16px;
  }

  .skeleton-value {
    width: 80px;
    height: 36px;
    margin-bottom: var(--ios-spacing-xs);
  }

  .skeleton-sub {
    width: 120px;
    height: 14px;
  }
}


.skeleton-chart {
  .skeleton-chart-header {
    margin-bottom: var(--ios-spacing-md);
  }

  .skeleton-chart-area {
    width: 100%;
    height: 340px;
    margin-bottom: var(--ios-spacing-lg);
    border-radius: var(--ios-radius-md);

    @include mobile { height: 280px; }
  }

  .skeleton-chart-legend {
    display: flex;
    justify-content: center;
    gap: var(--ios-spacing-lg);
  }

  .skeleton-legend-item {
    width: 60px;
    height: 12px;
  }
}


.skeleton-list {
  .skeleton-list-item {
    display: flex;
    align-items: center;
    gap: var(--ios-spacing-sm);
    padding: var(--ios-spacing-md) 0;
    border-bottom: 1px solid var(--ios-separator);

    &:last-child { border-bottom: none; }
  }

  .skeleton-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .skeleton-list-text {
    flex: 1;
    height: 16px;
  }

  .skeleton-list-value {
    width: 50px;
    height: 16px;
    flex-shrink: 0;
  }
}


.skeleton-generic {
  display: flex;
  flex-direction: column;
  gap: var(--ios-spacing-sm);

  .skeleton-line {
    height: 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pulse .skeleton-block {
    animation: none;
  }
}
</style>
