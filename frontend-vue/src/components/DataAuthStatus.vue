<template>
  <!--
    数据真实性状态提示组件：
    展示后端 data_provenance / data_freshness 信息，
    让用户清晰看到当前数据是否为真实采集、是否新鲜。
    依据：
    - is_real_data: 至少一个数据源采集到 >0 条且通过真实性校验
    - passed_count/source_count: 数据源通过比例
    - data_freshness.is_fresh: 数据是否在 24 小时内
    - fingerprints: 各数据源明细
  -->
  <div v-if="visible" class="data-auth-status" :class="statusClass" role="status" aria-live="polite">
    <div class="auth-status-icon">
      <el-icon :size="14">
        <component :is="statusIcon" />
      </el-icon>
    </div>
    <div class="auth-status-body">
      <span class="auth-status-title">{{ statusTitle }}</span>
      <span class="auth-status-detail">{{ statusDetail }}</span>
    </div>
    <el-popover v-if="hasDetails" placement="bottom" :width="380" trigger="hover">
      <template #reference>
        <el-icon class="auth-status-info" :size="14"><InfoFilled /></el-icon>
      </template>
      <div class="auth-detail-panel">
        <div class="detail-section">
          <div class="detail-section-title">数据溯源</div>
          <div class="detail-row">
            <span class="detail-label">真实数据</span>
            <span :class="['detail-value', provenance?.is_real_data ? 'value-ok' : 'value-warn']">
              {{ provenance?.is_real_data ? '是' : '否' }}
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">数据源通过</span>
            <span class="detail-value">{{ provenance?.passed_count ?? 0 }} / {{ provenance?.source_count ?? 0 }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">真实采集记录</span>
            <span class="detail-value">{{ formatNumber(provenance?.total_records ?? 0) }} 条</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">用户讨论源</span>
            <span :class="['detail-value', (provenance?.has_user_discussion ?? true) ? 'value-ok' : 'value-warn']">
              {{ (provenance?.has_user_discussion ?? true)
                ? `${provenance?.user_discussion_count ?? 0}/${provenance?.user_discussion_total ?? 0} 源有数据`
                : `0/${provenance?.user_discussion_total ?? 0} 源有数据（指数可能失真）`
              }}
            </span>
          </div>
          <div v-if="freshness" class="detail-row">
            <span class="detail-label">数据新鲜度</span>
            <span :class="['detail-value', freshness?.is_fresh ? 'value-ok' : 'value-warn']">
              {{ freshness?.is_fresh ? `新鲜（${freshness?.age_hours}小时前）` : `过期（${freshness?.stale_reason || '未知'}）` }}
            </span>
          </div>
        </div>
        <div v-if="fingerprints && fingerprints.length" class="detail-section">
          <div class="detail-section-title">数据源明细</div>
          <div v-for="fp in fingerprints" :key="fp.source_name" class="source-row">
            <span class="source-name">
              <span :class="['source-dot', fp.passed ? 'dot-ok' : 'dot-fail']"></span>
              {{ fp.source_name }}
            </span>
            <span class="source-count">{{ fp.record_count }} 条</span>
            <span :class="['source-status', fp.passed ? 'status-ok' : 'status-fail']">
              {{ fp.passed ? '通过' : '未通过' }}
            </span>
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CircleCheckFilled, WarningFilled, InfoFilled, CircleCloseFilled } from '@element-plus/icons-vue'

const props = defineProps({
  provenance: { type: Object, default: null },
  freshness: { type: Object, default: null }
})

// 是否展示该组件：未加载或后端不可用时不展示，避免误导
const visible = computed(() => {
  return props.provenance != null && typeof props.provenance === 'object'
})

const fingerprints = computed(() => props.provenance?.fingerprints || [])

const hasDetails = computed(() => {
  return fingerprints.value.length > 0 || props.freshness != null
})

// 综合状态判定：
// - all_pass_real: 所有数据源通过且有真实数据
// - partial_pass: 部分数据源未通过
// - stale: 数据已过期
// - no_user_discussion: 仅新闻源有数据，缺少用户讨论（指数可能失真）
// - no_real_data: 无任何真实数据
const statusLevel = computed(() => {
  if (!props.provenance) return 'unknown'
  const isReal = props.provenance.is_real_data
  const passedCount = props.provenance.passed_count ?? 0
  const sourceCount = props.provenance.source_count ?? 0
  const isFresh = props.freshness?.is_fresh ?? true
  // has_user_discussion: 是否有用户讨论源（股吧/小红书/雪球）采集到 >0 条
  // 若为 false，说明仅有新闻/资讯，指数会因缺少小白语境失真
  const hasUserDiscussion = props.provenance.has_user_discussion ?? true

  if (!isReal) return 'no_real_data'
  if (!isFresh) return 'stale'
  if (!hasUserDiscussion) return 'no_user_discussion'
  if (passedCount < sourceCount) return 'partial_pass'
  return 'all_pass_real'
})

const statusClass = computed(() => `status-${statusLevel.value}`)

const statusIcon = computed(() => {
  switch (statusLevel.value) {
    case 'all_pass_real': return CircleCheckFilled
    case 'partial_pass': return WarningFilled
    case 'stale': return WarningFilled
    case 'no_user_discussion': return WarningFilled
    case 'no_real_data': return CircleCloseFilled
    default: return InfoFilled
  }
})

const statusTitle = computed(() => {
  switch (statusLevel.value) {
    case 'all_pass_real': return '真实数据'
    case 'partial_pass': return '数据部分异常'
    case 'stale': return '数据已过期'
    case 'no_user_discussion': return '缺少用户讨论'
    case 'no_real_data': return '暂无真实数据'
    default: return '数据状态未知'
  }
})

const statusDetail = computed(() => {
  const p = props.provenance
  if (!p) return ''
  const passedCount = p.passed_count ?? 0
  const sourceCount = p.source_count ?? 0
  const total = p.total_records ?? 0
  switch (statusLevel.value) {
    case 'all_pass_real':
      return `${passedCount}/${sourceCount} 源通过 · ${formatNumber(total)} 条真实数据`
    case 'partial_pass':
      return `${passedCount}/${sourceCount} 源通过 · ${formatNumber(total)} 条数据`
    case 'stale':
      return props.freshness?.stale_reason || '数据已过期，请等待下次自动采集'
    case 'no_user_discussion':
      return `仅新闻源有数据，股吧/小红书/雪球均为空，指数可能失真`
    case 'no_real_data':
      return '所有数据源采集为空或未通过真实性校验'
    default:
      return ''
  }
})

function formatNumber(num) {
  if (num === null || num === undefined) return '0'
  return Number(num).toLocaleString('zh-CN')
}
</script>

<style scoped lang="scss">
.data-auth-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  line-height: 1.4;
  border: 1px solid transparent;
  transition: all 0.2s ease;

  .auth-status-icon {
    display: flex;
    align-items: center;
  }

  .auth-status-body {
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .auth-status-title {
    font-weight: 600;
  }

  .auth-status-detail {
    font-size: 11px;
    opacity: 0.85;
  }

  .auth-status-info {
    cursor: help;
    opacity: 0.7;
    &:hover { opacity: 1; }
  }
}

.status-all_pass_real {
  color: #10b981;
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.2);
}

.status-partial_pass {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.2);
}

.status-stale {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.2);
}

.status-no_user_discussion {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.08);
  border-color: rgba(245, 158, 11, 0.2);
}

.status-no_real_data {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.2);
}

.status-unknown {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.08);
  border-color: rgba(107, 114, 128, 0.2);
}

.auth-detail-panel {
  font-size: 12px;
  max-height: 320px;
  overflow-y: auto;

  .detail-section {
    margin-bottom: 12px;
    &:last-child { margin-bottom: 0; }
  }

  .detail-section-title {
    font-weight: 600;
    margin-bottom: 6px;
    color: #1f2937;
  }

  .detail-row {
    display: flex;
    justify-content: space-between;
    padding: 3px 0;
    color: #4b5563;
  }

  .detail-label { opacity: 0.8; }
  .detail-value { font-weight: 500; }
  .value-ok { color: #10b981; }
  .value-warn { color: #f59e0b; }

  .source-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 3px 0;
    border-bottom: 1px solid #f3f4f6;
    &:last-child { border-bottom: none; }
  }

  .source-name {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .source-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }

  .dot-ok { background: #10b981; }
  .dot-fail { background: #ef4444; }

  .source-count {
    color: #6b7280;
    font-size: 11px;
  }

  .source-status {
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 8px;
  }

  .status-ok {
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
  }

  .status-fail {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
  }
}
</style>
