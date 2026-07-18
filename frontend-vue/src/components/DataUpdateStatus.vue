<template>
  <div class="data-update-status" :class="statusClass" :title="tooltip">
    <el-icon :size="14" class="status-icon">
      <component :is="statusIcon" />
    </el-icon>
    <span class="status-text">{{ statusText }}</span>
    <el-progress
      v-if="isRunning"
      :percentage="progress"
      :show-text="false"
      :stroke-width="3"
      class="status-progress"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheck, CircleClose, InfoFilled } from '@element-plus/icons-vue'
import { getCollectionStatus } from '@/api/index'

const status = ref('idle')
const progress = ref(0)
const message = ref('等待启动')
const error = ref('')
const retryCount = ref(0)
const maxRetries = ref(3)
const lastFinishedAt = ref(null)
const lastSuccessAt = ref(null)
const nextRunAt = ref(null)
const trigger = ref('idle')
const intervalSeconds = ref(1800)
// 每秒触发的 tick，用于倒计时实时刷新
const tick = ref(0)

const isRunning = computed(() => status.value === 'running')

const statusClass = computed(() => {
  switch (status.value) {
    case 'running': return 'status-running'
    case 'success': return 'status-success'
    case 'failed': return 'status-failed'
    default: return 'status-idle'
  }
})

const statusIcon = computed(() => {
  switch (status.value) {
    case 'running': return Loading
    case 'success': return CircleCheck
    case 'failed': return CircleClose
    default: return InfoFilled
  }
})

const statusText = computed(() => {
  switch (status.value) {
    case 'running': return `数据更新中 ${progress.value}%`
    case 'success': return nextRunText.value || '数据已更新'
    case 'failed': return '数据更新失败'
    default: return message.value || '等待数据更新'
  }
})

const nextRunText = computed(() => {
  // 依赖 tick 触发每秒重新计算
  void tick.value
  if (!nextRunAt.value) return ''
  try {
    const date = new Date(nextRunAt.value)
    if (isNaN(date.getTime())) return ''
    const now = new Date()
    const diff = date - now
    if (diff <= 0) return '即将更新'
    const mins = Math.floor(diff / 60000)
    const secs = Math.floor((diff % 60000) / 1000)
    return `下次更新 ${mins}分${secs.toString().padStart(2, '0')}秒后`
  } catch {
    return ''
  }
})

const triggerLabel = computed(() => {
  switch (trigger.value) {
    case 'startup': return '启动采集'
    case 'scheduled': return '定时采集'
    case 'manual': return '手动采集'
    default: return ''
  }
})

const tooltip = computed(() => {
  const parts = []
  if (triggerLabel.value) parts.push(`触发方式: ${triggerLabel.value}`)
  parts.push(message.value)
  if (error.value) parts.push(`错误: ${error.value}`)
  if (lastSuccessAt.value) parts.push(`上次成功: ${formatTime(lastSuccessAt.value)}`)
  if (nextRunAt.value) parts.push(`下次定时: ${formatTime(nextRunAt.value)}`)
  parts.push(`采集间隔: ${Math.floor(intervalSeconds.value / 60)} 分钟`)
  return parts.filter(Boolean).join('\n')
})

function formatTime(timeStr) {
  if (!timeStr) return ''
  try {
    const date = new Date(timeStr)
    if (isNaN(date.getTime())) return timeStr
    return date.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch {
    return timeStr
  }
}

async function fetchStatus() {
  try {
    const res = await getCollectionStatus()
    const data = res?.data ?? res
    if (!data) return

    const prevStatus = status.value
    status.value = data.status || 'idle'
    progress.value = data.progress ?? 0
    message.value = data.message || ''
    error.value = data.error || ''
    retryCount.value = data.retry_count ?? 0
    maxRetries.value = data.max_retries ?? 3
    lastFinishedAt.value = data.finished_at || null
    lastSuccessAt.value = data.last_success_at || null
    nextRunAt.value = data.next_run_at || null
    trigger.value = data.trigger || 'idle'
    intervalSeconds.value = data.interval_seconds ?? 1800

    // 状态发生变化时给出提示
    if (prevStatus === 'running' && status.value === 'failed') {
      ElMessage.error(`数据更新失败${retryCount.value < maxRetries.value ? '，正在重试...' : ''}`)
    } else if (prevStatus === 'running' && status.value === 'success') {
      ElMessage.success('市场数据已更新')
    }
  } catch (e) {
    // 状态查询失败不阻塞界面
    console.error('获取数据更新状态失败:', e)
  }
}

let timer = null
let tickTimer = null

onMounted(() => {
  fetchStatus()
  // 每 3 秒轮询一次，配合 WebSocket 实时推送兜底
  timer = setInterval(fetchStatus, 3000)
  // 每秒触发 tick，刷新倒计时显示
  tickTimer = setInterval(() => { tick.value++ }, 1000)
})

onUnmounted(() => {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (tickTimer) {
    clearInterval(tickTimer)
    tickTimer = null
  }
})
</script>

<style lang="scss" scoped>
.data-update-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(148, 163, 184, 0.1);
  color: #94a3b8;
  // 避免 transition: all 导致浏览器为所有属性准备动画资源
  transition: background-color 0.2s ease, color 0.2s ease;
  max-width: 180px;
  // 限制绘制范围，避免状态变化导致整行重绘
  contain: layout paint;

  .status-icon {
    flex-shrink: 0;
  }

  .status-text {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-progress {
    width: 40px;
    flex-shrink: 0;
  }

  &.status-running {
    background: rgba(14, 165, 233, 0.12);
    color: #38bdf8;

    .status-icon {
      animation: rotate 1.5s linear infinite;
    }
  }

  &.status-success {
    background: rgba(34, 197, 94, 0.12);
    color: #4ade80;
  }

  &.status-failed {
    background: rgba(239, 68, 68, 0.12);
    color: #f87171;
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
